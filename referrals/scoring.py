import datetime
from CTFd.models import Awards, Challenges, Solves, Users, Teams, db
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.models import Referrals


class ReferralScoring:
    @staticmethod
    def is_referral_accessible_for_user(user=None):
        """
        Determines whether the referral system is accessible for the specified user.
        Checks:
        1. Authentication
        2. Admin bypass
        3. Competition paused
        4. Plugin master enabled
        5. User banned or hidden
        6. User or team suspension from referral program
        7. Referrer Access Gate (Points, Solves, or Prerequisite Challenge)
        Returns: (is_accessible: bool, message: str)
        """
        if user is None:
            user = get_current_user()

        if not user:
            return False, "Authentication required."

        # Admins always have access to manage and preview
        if getattr(user, "type", None) == "admin":
            return True, ""

        # 1. CTFd Pause check
        if get_config("paused"):
            return False, "Competition is currently paused."

        # 2. Master Referral System toggle
        if not ReferralConfig.get_bool("referral_enabled"):
            return False, "Referral system is currently disabled."

        # 3. User banned or hidden
        if getattr(user, "banned", False) or getattr(user, "hidden", False):
            return False, "Account access restricted."

        # 4. User or Team suspension from referrals
        if ReferralConfig.is_user_disabled(user.id):
            return False, "Your referral privileges have been suspended."

        if getattr(user, "team_id", None) and ReferralConfig.is_team_disabled(user.team_id):
            return False, "Your team's referral privileges have been suspended."

        # 5. Referrer Access Gate (Prerequisite training / solves / points)
        mode = ReferralConfig.get("referral_unlock_mode", "none")
        if mode != "none":
            req_points = ReferralConfig.get_int("referral_unlock_min_points")
            req_solves = ReferralConfig.get_int("referral_unlock_min_solves")
            target_chal_id = ReferralConfig.get("referral_unlock_challenge_id")

            # Calculate user's score & solves
            user_solves = Solves.query.filter_by(user_id=user.id).all()
            user_points = sum((s.challenge.value or 0) for s in user_solves if s.challenge)
            user_solves_count = len(user_solves)

            solved_target = False
            target_name = "prerequisite challenge"
            if target_chal_id:
                try:
                    target_id_int = int(target_chal_id)
                    solved_target = any(s.challenge_id == target_id_int for s in user_solves)
                    target_obj = Challenges.query.filter_by(id=target_id_int).first()
                    if target_obj:
                        target_name = f"'{target_obj.name}'"
                except (ValueError, TypeError):
                    solved_target = False

            meets_pts = (user_points >= req_points) if req_points > 0 else True
            meets_solves = (user_solves_count >= req_solves) if req_solves > 0 else True
            meets_chal = solved_target if target_chal_id else True

            unlocked = False
            reason = "Prerequisite training requirements not yet met."

            if mode == "points":
                unlocked = meets_pts
                reason = f"Unlock requirement: Score at least {req_points} points (Current: {user_points} PTS)."
            elif mode == "solves":
                unlocked = meets_solves
                reason = f"Unlock requirement: Solve at least {req_solves} challenges (Current: {user_solves_count} solves)."
            elif mode == "challenge":
                unlocked = meets_chal
                reason = f"Unlock requirement: Solve challenge {target_name} to unlock recruitment directives."
            elif mode in ("all", "both"):
                unlocked = (meets_pts and meets_solves and meets_chal)
                reason = f"Unlock requirement: Meet all criteria ({req_points} PTS, {req_solves} solves, and {target_name})."
            elif mode == "any":
                unlocked = (
                    (req_points > 0 and meets_pts) or
                    (req_solves > 0 and meets_solves) or
                    (target_chal_id and meets_chal)
                )
                reason = "Unlock requirement: Complete at least one prerequisite training milestone."

            if not unlocked:
                custom_msg = ReferralConfig.get("referral_access_denied_message")
                return False, custom_msg or reason

        return True, ""
    @staticmethod
    def get_referee_progress(referee_id, connection=None):
        """
        Calculates legitimate challenge solves and score for a recruit operative.
        """
        if connection is not None:
            # Connection-level query safe for flush events
            rows = connection.execute(
                db.select(Challenges.value)
                .join(Solves, Solves.challenge_id == Challenges.id)
                .where(Solves.user_id == referee_id)
            ).fetchall()
            exclude_zero = ReferralConfig.get_bool("referral_exclude_zero_point_chals")
            valid_vals = [r[0] for r in rows if r[0] is not None and (not exclude_zero or r[0] > 0)]
            return sum(valid_vals), len(valid_vals)

        solves = Solves.query.filter_by(user_id=referee_id).all()
        exclude_zero = ReferralConfig.get_bool("referral_exclude_zero_point_chals")

        valid_solves = []
        for s in solves:
            if s.challenge:
                val = s.challenge.value or 0
                if exclude_zero and val <= 0:
                    continue
                valid_solves.append(s)

        score = sum((s.challenge.value or 0) for s in valid_solves)
        solve_count = len(valid_solves)
        return score, solve_count

    @staticmethod
    def check_and_qualify(referral, connection=None):
        """
        Checks whether the given referral meets the configured milestone and mints awards.
        Supports both connection-level execution (inside after_insert hooks) and session-level execution.
        """
        if not referral:
            return False, "Referral not found"

        if referral.status in ("qualified", "rejected", "revoked"):
            return False, f"Referral is already {referral.status}"

        # Do not automatically qualify flagged referrals without admin approval
        if referral.status == "flagged":
            return False, "Referral is flagged for administrative review."

        score, solve_count = ReferralScoring.get_referee_progress(referral.referee_id, connection=connection)
        min_points = ReferralConfig.get_int("referral_min_points_to_qualify")
        min_solves = ReferralConfig.get_int("referral_min_solves_to_qualify")

        meets_points = (score >= min_points)
        meets_solves = (solve_count >= min_solves)

        qual_mode = ReferralConfig.get("referral_qualification_mode", "points_only")
        req_chal_id = ReferralConfig.get("referral_required_challenge_id")

        solved_required_chal = False
        if req_chal_id:
            try:
                req_chal_id_int = int(req_chal_id)
                if connection is not None:
                    row = connection.execute(
                        db.select(Solves.id).where(
                            Solves.user_id == referral.referee_id,
                            Solves.challenge_id == req_chal_id_int,
                        )
                    ).first()
                    solved_required_chal = (row is not None)
                else:
                    solved_required_chal = (
                        Solves.query.filter_by(
                            user_id=referral.referee_id,
                            challenge_id=req_chal_id_int,
                        ).first()
                        is not None
                    )
            except (ValueError, TypeError):
                solved_required_chal = False

        is_qualified = False
        if qual_mode == "challenge_only":
            is_qualified = solved_required_chal
            reason_msg = f"Requires solving designated challenge (Solved: {solved_required_chal})."
        elif qual_mode == "both":
            is_qualified = (meets_points and meets_solves and solved_required_chal)
            reason_msg = f"Progress: {score}/{min_points} PTS, {solve_count}/{min_solves} solves, designated challenge solved: {solved_required_chal}."
        elif qual_mode == "either":
            is_qualified = ((meets_points and meets_solves) or solved_required_chal)
            reason_msg = f"Progress: {score}/{min_points} PTS, {solve_count}/{min_solves} solves, designated challenge solved: {solved_required_chal}."
        else:  # points_only (default)
            is_qualified = (meets_points and meets_solves)
            reason_msg = f"Progress: {score}/{min_points} PTS, {solve_count}/{min_solves} solves."

        if not is_qualified:
            return False, reason_msg

        user_mode = get_config("user_mode")
        max_cap = ReferralConfig.get_int("referral_max_per_account")

        # Cap check
        if max_cap > 0:
            if connection is not None:
                if user_mode == "teams" and referral.referrer_team_id:
                    awarded_count = connection.execute(
                        db.select(db.func.count(Referrals.id)).where(
                            Referrals.referrer_team_id == referral.referrer_team_id,
                            Referrals.status == "qualified",
                            Referrals.award_id.isnot(None),
                        )
                    ).scalar() or 0
                else:
                    awarded_count = connection.execute(
                        db.select(db.func.count(Referrals.id)).where(
                            Referrals.referrer_id == referral.referrer_id,
                            Referrals.status == "qualified",
                            Referrals.award_id.isnot(None),
                        )
                    ).scalar() or 0
            else:
                if user_mode == "teams" and referral.referrer_team_id:
                    awarded_count = Referrals.query.filter(
                        Referrals.referrer_team_id == referral.referrer_team_id,
                        Referrals.status == "qualified",
                        Referrals.award_id.isnot(None),
                    ).count()
                else:
                    awarded_count = Referrals.query.filter(
                        Referrals.referrer_id == referral.referrer_id,
                        Referrals.status == "qualified",
                        Referrals.award_id.isnot(None),
                    ).count()

            if awarded_count >= max_cap:
                notes = (referral.notes or "") + f" | Qualified with {score} PTS, but recruiter cap of {max_cap} reached (0 PTS minted)."
                if connection is not None:
                    connection.execute(
                        Referrals.__table__.update()
                        .where(Referrals.id == referral.id)
                        .values(status="cap_reached", qualified_at=datetime.datetime.utcnow(), notes=notes)
                    )
                else:
                    referral.status = "cap_reached"
                    referral.qualified_at = datetime.datetime.utcnow()
                    referral.notes = notes
                    db.session.commit()
                return False, "Qualification reached, but recruiter cap was already reached."

        # Global ceiling check
        global_cap = ReferralConfig.get_int("referral_global_point_cap")
        award_val = ReferralConfig.get_int("referral_points")
        category = ReferralConfig.get("referral_award_category", "Recruitment Directive")

        if global_cap > 0:
            if connection is not None:
                current_total = connection.execute(
                    db.select(db.func.sum(Awards.value)).where(Awards.category == category)
                ).scalar() or 0
            else:
                current_total = db.session.query(db.func.sum(Awards.value)).filter_by(category=category).scalar() or 0

            if current_total + award_val > global_cap:
                notes = (referral.notes or "") + f" | Global CTF referral ceiling ({global_cap} PTS) reached."
                if connection is not None:
                    connection.execute(
                        Referrals.__table__.update()
                        .where(Referrals.id == referral.id)
                        .values(status="cap_reached", qualified_at=datetime.datetime.utcnow(), notes=notes)
                    )
                else:
                    referral.status = "cap_reached"
                    referral.qualified_at = datetime.datetime.utcnow()
                    referral.notes = notes
                    db.session.commit()
                return False, "Global referral point cap reached."

        ref_team_id = referral.referrer_team_id if user_mode == "teams" else None
        referee_name = referral.referee.name if referral.referee else f"Operative #{referral.referee_id}"
        notes = (referral.notes or "") + f" | Field verified with {score} PTS ({solve_count} solves)."

        if connection is not None:
            # 1. Mint Referrer Award via connection
            res = connection.execute(
                Awards.__table__.insert().values(
                    user_id=referral.referrer_id,
                    team_id=ref_team_id,
                    name=f"Recruitment Bonus: {referee_name}",
                    description=f"Awarded for recruiting active operative {referee_name} who proved field capability with {score} points across {solve_count} solves.",
                    value=award_val,
                    category=category,
                    date=datetime.datetime.utcnow(),
                )
            )
            award_id = res.inserted_primary_key[0] if res.inserted_primary_key else None

            # 2. Mint Recruit Welcome Award if enabled
            referee_award_id = None
            if ReferralConfig.get_bool("referral_referee_bonus_enabled"):
                recruit_points = ReferralConfig.get_int("referral_referee_bonus_points")
                if recruit_points > 0:
                    rec_team_id = referral.referee_team_id if user_mode == "teams" else None
                    rec_res = connection.execute(
                        Awards.__table__.insert().values(
                            user_id=referral.referee_id,
                            team_id=rec_team_id,
                            name="Recruit Welcome Bonus",
                            description=f"Welcome bonus for qualifying as a recruited operative under code {referral.code_used}.",
                            value=recruit_points,
                            category=category,
                            date=datetime.datetime.utcnow(),
                        )
                    )
                    referee_award_id = rec_res.inserted_primary_key[0] if rec_res.inserted_primary_key else None

            # 3. Update referral row
            connection.execute(
                Referrals.__table__.update()
                .where(Referrals.id == referral.id)
                .values(
                    status="qualified",
                    award_id=award_id,
                    referee_award_id=referee_award_id,
                    qualified_at=datetime.datetime.utcnow(),
                    notes=notes,
                )
            )
        else:
            # Session-level execution
            referrer_award = Awards(
                user_id=referral.referrer_id,
                team_id=ref_team_id,
                name=f"Recruitment Bonus: {referee_name}",
                description=f"Awarded for recruiting active operative {referee_name} who proved field capability with {score} points across {solve_count} solves.",
                value=award_val,
                category=category,
            )
            db.session.add(referrer_award)
            db.session.flush()
            referral.award_id = referrer_award.id

            if ReferralConfig.get_bool("referral_referee_bonus_enabled"):
                recruit_points = ReferralConfig.get_int("referral_referee_bonus_points")
                if recruit_points > 0:
                    rec_team_id = referral.referee_team_id if user_mode == "teams" else None
                    referee_award = Awards(
                        user_id=referral.referee_id,
                        team_id=rec_team_id,
                        name="Recruit Welcome Bonus",
                        description=f"Welcome bonus for qualifying as a recruited operative under code {referral.code_used}.",
                        value=recruit_points,
                        category=category,
                    )
                    db.session.add(referee_award)
                    db.session.flush()
                    referral.referee_award_id = referee_award.id

            referral.status = "qualified"
            referral.qualified_at = datetime.datetime.utcnow()
            referral.notes = notes
            db.session.commit()

        return True, f"Successfully qualified! Minted +{award_val} PTS award."

    @staticmethod
    def approve_flagged_referral(referral_id):
        referral = Referrals.query.filter_by(id=referral_id).first()
        if not referral:
            return False, "Referral not found."

        referral.status = "pending"
        referral.notes = (referral.notes or "") + " | Admin cleared fraud flag."
        db.session.commit()

        qualified, msg = ReferralScoring.check_and_qualify(referral)
        if qualified:
            return True, f"Flag cleared and recruit immediately qualified (+{ReferralConfig.get_int('referral_points')} PTS minted)!"
        return True, "Flag cleared. Referral is now pending qualification milestone."

    @staticmethod
    def revoke_referral(referral_id, reason="Admin revoked"):
        referral = Referrals.query.filter_by(id=referral_id).first()
        if not referral:
            return False, "Referral not found."

        if referral.award_id:
            award = Awards.query.filter_by(id=referral.award_id).first()
            if award:
                db.session.delete(award)
            referral.award_id = None

        if referral.referee_award_id:
            rec_award = Awards.query.filter_by(id=referral.referee_award_id).first()
            if rec_award:
                db.session.delete(rec_award)
            referral.referee_award_id = None

        referral.status = "revoked"
        referral.notes = (referral.notes or "") + f" | {reason}"
        db.session.commit()
        return True, "Referral revoked and scoreboard awards cleanly removed."
