const profileForm = document.getElementById("profile-form");
const messageForm = document.getElementById("message-form");
const statusText = document.getElementById("status");
const messageStatus = document.getElementById("message-status");
const driversContainer = document.getElementById("drivers");
const passengersContainer = document.getElementById("passengers");

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.remove("success", "error");
  element.classList.add(isError ? "error" : "success");
}

function profileTemplate(profile) {
  const carDetails = profile.role === "driver"
    ? `Car: ${profile.car_make || "-"} ${profile.car_model || ""} | Plate: ${profile.plate_number || "-"} | Seats: ${profile.seats_available || 0}`
    : "Passenger";

  return `
    <article class="profile">
      <h3>#${profile.id} - ${profile.full_name}</h3>
      <small><strong>Route:</strong> ${profile.home_area} → ${profile.destination_area}</small>
      <small><strong>Schedule:</strong> ${profile.commute_days.join(", ")} | ${profile.depart_time} / ${profile.return_time}</small>
      <small><strong>${carDetails}</strong></small>
      <small><strong>Contact:</strong> ${profile.phone} | ${profile.email}</small>
      <small><strong>Notes:</strong> ${profile.notes || "N/A"}</small>
    </article>
  `;
}

async function loadProfiles() {
  const [driversResponse, passengersResponse] = await Promise.all([
    fetch("/api/profiles?role=driver"),
    fetch("/api/profiles?role=passenger"),
  ]);

  const drivers = await driversResponse.json();
  const passengers = await passengersResponse.json();

  driversContainer.innerHTML = drivers.length ? drivers.map(profileTemplate).join("") : "<p>No drivers yet.</p>";
  passengersContainer.innerHTML = passengers.length ? passengers.map(profileTemplate).join("") : "<p>No passengers yet.</p>";
}

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(profileForm);
  const commuteDays = formData.getAll("commute_days");
  const payload = {
    role: formData.get("role"),
    full_name: formData.get("full_name"),
    phone: formData.get("phone"),
    email: formData.get("email"),
    home_area: formData.get("home_area"),
    destination_area: formData.get("destination_area"),
    commute_days: commuteDays,
    depart_time: formData.get("depart_time"),
    return_time: formData.get("return_time"),
    car_make: formData.get("car_make"),
    car_model: formData.get("car_model"),
    car_color: formData.get("car_color"),
    plate_number: formData.get("plate_number"),
    seats_available: formData.get("seats_available") ? Number(formData.get("seats_available")) : null,
    notes: formData.get("notes"),
  };

  try {
    const response = await fetch("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Unable to save profile");
    }

    profileForm.reset();
    setStatus(statusText, `Profile saved with ID #${result.id}`);
    await loadProfiles();
  } catch (error) {
    setStatus(statusText, error.message, true);
  }
});

messageForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(messageForm);
  const payload = {
    sender_id: Number(formData.get("sender_id")),
    receiver_id: Number(formData.get("receiver_id")),
    proposed_fuel_share: formData.get("proposed_fuel_share")
      ? Number(formData.get("proposed_fuel_share"))
      : null,
    message: formData.get("message"),
  };

  try {
    const response = await fetch("/api/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not send message");
    }

    messageForm.reset();
    setStatus(
      messageStatus,
      `Message sent from #${result.sender_id} to #${result.receiver_id}${
        result.proposed_fuel_share ? ` | PKR ${result.proposed_fuel_share}` : ""
      }`
    );
  } catch (error) {
    setStatus(messageStatus, error.message, true);
  }
});

loadProfiles().catch(() => {
  setStatus(statusText, "Unable to load profiles right now.", true);
});
