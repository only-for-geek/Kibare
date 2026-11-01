const statusLabel = document.getElementById("status-label");
const statusDot = document.getElementById("status-dot");

async function checkMatrixAvailability() {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 4000);

  try {
    const response = await fetch("/health/matrix", {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("Matrix API unavailable");
    const versions = await response.json();
    if (!Array.isArray(versions.versions)) throw new Error("Invalid Matrix response");

    statusLabel.textContent = "Serveur Matrix disponible";
    statusDot.classList.remove("status-checking", "status-offline");
  } catch {
    statusLabel.textContent = "Serveur Matrix indisponible";
    statusDot.classList.remove("status-checking");
    statusDot.classList.add("status-offline");
  } finally {
    window.clearTimeout(timeout);
  }
}

checkMatrixAvailability();
