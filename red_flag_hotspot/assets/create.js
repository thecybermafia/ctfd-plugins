CTFd.plugin.run((_CTFd) => {
  if (window.initRedFlagHotspotAdmin) {
    window.initRedFlagHotspotAdmin();
  } else {
    const script = document.createElement("script");
    script.src = "/plugins/red_flag_hotspot/assets/admin-editor.js";
    script.onload = () => {
      if (window.initRedFlagHotspotAdmin) window.initRedFlagHotspotAdmin();
    };
    document.head.appendChild(script);
  }
});
