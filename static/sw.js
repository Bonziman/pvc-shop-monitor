self.addEventListener("push", function(e) {
  const data = e.data.text();
  e.waitUntil(
    self.registration.showNotification("PVC Trade Alert", {
      body: data,
      icon: "https://minecraft.wiki/images/emerald.png" // optional
    })
  );
});

