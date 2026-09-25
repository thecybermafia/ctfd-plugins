import datetime
from CTFd.models import Awards, Challenges, Solves, Users, Teams, db
from CTFd.utils import get_config
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.models import Referrals


class ReferralScoring:
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

        if not (meets_points and meets_solves):
            return False, f"Progress: {score}/{min_points} PTS, {solve_count}/{min_solves} solves."

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
