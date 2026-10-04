/**
 * ui/app.js: Transkript Sinematik Arayüz Mantığı ve pywebview API Entegrasyonu
 */

// DOM Öğeleri
const audioHeroCard = document.getElementById("audioHeroCard");
const heroIdleView = document.getElementById("heroIdleView");
const heroSelectedView = document.getElementById("heroSelectedView");
const btnSelectFile = document.getElementById("btnSelectFile");
const selectedFileName = document.getElementById("selectedFileName");
const fileMeta = document.getElementById("fileMeta");
const btnTranscribe = document.getElementById("btnTranscribe");
const progressSection = document.getElementById("progressSection");
const statusMessage = document.getElementById("statusMessage");
const progressPercent = document.getElementById("progressPercent");
const progressBar = document.getElementById("progressBar");
const errorMessage = document.getElementById("errorMessage");
const transcriptText = document.getElementById("transcriptText");
const transcriptEmptyState = document.getElementById("transcriptEmptyState");
const transcriptLiveStats = document.getElementById("transcriptLiveStats");
const btnCopy = document.getElementById("btnCopy");
const customTermsInput = document.getElementById("customTerms");

let isTranscribing = false;
let bridgeReady = false;

// Hata göster / gizle
function showError(msg) {
  if (!msg) {
    errorMessage.classList.add("hidden");
    errorMessage.textContent = "";
  } else {
    console.error("[UI Hata]", msg);
    errorMessage.textContent = msg;
    errorMessage.classList.remove("hidden");
  }
}

// pywebview API köprüsünün hazır olduğunu doğrula
function setupBridge() {
  if (bridgeReady) return;
  if (window.pywebview && window.pywebview.api) {
    bridgeReady = true;
    btnSelectFile.disabled = false;
    console.log("[JS API] pywebview köprüsü başarıyla bağlandı.");
  }
}

window.addEventListener("pywebviewready", setupBridge);
document.addEventListener("DOMContentLoaded", () => {
  setupBridge();
  if (window.TranskriptMotion) {
    window.TranskriptMotion.setupTactileButtons();
    window.TranskriptMotion.setupPointerHighlight();
  }
});

const bridgeCheckInterval = setInterval(() => {
  setupBridge();
  if (bridgeReady) {
    clearInterval(bridgeCheckInterval);
  }
}, 150);

// Hero Sahnesi Tıklaması (Doğrudan butona basılmadıysa dosya seçiciyi açar)
if (audioHeroCard) {
  audioHeroCard.addEventListener("click", (e) => {
    if (isTranscribing) return;
    if (e.target.closest("#btnSelectFile")) return; // Butonun kendi event'i çalışsın
    btnSelectFile.click();
  });
}

// Boş Durum Tıklaması (Textarea'ya odaklanır)
if (transcriptEmptyState) {
  transcriptEmptyState.addEventListener("click", () => {
    transcriptText.focus();
  });
}

// Textarea Değişim Dinleyicisi (Boş durum görünürlüğünü senkronize eder)
transcriptText.addEventListener("input", () => {
  updateTranscriptVisualState();
});

function updateTranscriptVisualState() {
  const hasText = transcriptText.value && transcriptText.value.trim().length > 0;
  if (hasText) {
    if (transcriptEmptyState) {
      transcriptEmptyState.classList.add("hidden-state");
    }
    btnCopy.disabled = false;
    if (transcriptLiveStats) {
      transcriptLiveStats.textContent = `${transcriptText.value.length} karakter`;
      transcriptLiveStats.classList.remove("hidden");
    }
  } else {
    if (transcriptEmptyState && !isTranscribing) {
      transcriptEmptyState.classList.remove("hidden-state");
    }
    btnCopy.disabled = true;
    if (transcriptLiveStats) {
      transcriptLiveStats.classList.add("hidden");
    }
  }
}

// Ses Dosyası Seç Butonu Olayı
btnSelectFile.addEventListener("click", async (e) => {
  e.stopPropagation();
  if (isTranscribing) return;
  showError(null);

  if (!window.pywebview || !window.pywebview.api) {
    showError("Masaüstü köprüsü henüz hazır değil. Lütfen bir saniye sonra tekrar deneyin.");
    return;
  }

  btnSelectFile.disabled = true;
  const selectLabel = btnSelectFile.querySelector(".btn-select-label") || btnSelectFile;
  const originalSelectText = selectLabel.textContent;
  selectLabel.textContent = "Seçiliyor...";

  try {
    console.log("[UI] select_file API çağrılıyor...");
    const res = await window.pywebview.api.select_file();
    console.log("[UI] select_file yanıtı:", res);

    if (res.success && res.info) {
      selectedFileName.textContent = res.info.file_name;
      selectedFileName.classList.add("active");

      const minutes = Math.floor(res.info.duration_seconds / 60);
      const seconds = Math.floor(res.info.duration_seconds % 60);
      const ext = (res.info.extension || "").toUpperCase().replace(".", "");
      fileMeta.textContent = `Süre: ${minutes} dk ${seconds} sn | Boyut: ${res.info.size_mb} MB | Format: ${ext}`;

      // Hero sahnesini seçili duruma dönüştür
      if (audioHeroCard) {
        audioHeroCard.classList.remove("state-idle");
        audioHeroCard.classList.add("state-selected");
      }
      selectLabel.textContent = "Değiştir";

      btnTranscribe.disabled = false;
    } else if (res.error) {
      showError(res.error);
      selectLabel.textContent = originalSelectText;
    } else if (res.cancelled) {
      console.log("[UI] Dosya seçimi iptal edildi.");
      selectLabel.textContent = originalSelectText;
    }
  } catch (err) {
    console.error("[UI] Dosya seçimi JS hatası:", err);
    showError("Dosya seçiminde hata oluştu: " + err.message);
    selectLabel.textContent = originalSelectText;
  } finally {
    btnSelectFile.disabled = false;
  }
});

// Metne Dönüştür Butonu Olayı
btnTranscribe.addEventListener("click", async () => {
  if (isTranscribing) return;
  showError(null);

  if (!window.pywebview || !window.pywebview.api) {
    showError("Masaüstü köprüsü hazır değil.");
    return;
  }

  isTranscribing = true;
  btnSelectFile.disabled = true;
  btnTranscribe.disabled = true;
  if (customTermsInput) {
    customTermsInput.disabled = true;
  }
  btnCopy.disabled = true;
  transcriptText.value = "";
  if (transcriptEmptyState) {
    transcriptEmptyState.classList.add("hidden-state");
  }
  if (transcriptLiveStats) {
    transcriptLiveStats.classList.add("hidden");
    transcriptLiveStats.textContent = "0 karakter";
  }

  // Hero sahnesini transkripsiyon moduna al
  if (audioHeroCard) {
    audioHeroCard.classList.remove("state-selected", "state-completed");
    audioHeroCard.classList.add("state-transcribing");
  }

  // Buton etiketini güncelle
  const btnLabel = btnTranscribe.querySelector(".btn-label-text") || btnTranscribe;
  btnLabel.textContent = "İşleniyor...";

  progressSection.classList.remove("hidden");
  progressBar.style.width = "0%";
  progressPercent.textContent = "%0";
  statusMessage.textContent = "Hazırlanıyor...";

  try {
    const customTerms = customTermsInput ? customTermsInput.value : "";
    console.log("[UI] start_transcription API çağrılıyor...");
    const res = await window.pywebview.api.start_transcription(customTerms);
    if (!res.success) {
      showError(res.error || "Transkripsiyon başlatılamadı.");
      resetStateAfterCompletion();
    }
  } catch (err) {
    showError("İşlem başlatma hatası: " + err.message);
    resetStateAfterCompletion();
  }
});

// Python tarafından evaluate_js ile çağrılan global fonksiyon: updateProgress
window.updateProgress = function(percent, status, text) {
  progressBar.style.width = percent + "%";
  progressPercent.textContent = "%" + percent;
  
  if (percent >= 100) {
    statusMessage.textContent = "Transkript hazır";
    if (audioHeroCard) {
      audioHeroCard.classList.remove("state-transcribing");
      audioHeroCard.classList.add("state-completed");
    }
  } else {
    statusMessage.textContent = status;
    const btnLabel = btnTranscribe.querySelector(".btn-label-text");
    if (btnLabel && isTranscribing) {
      btnLabel.textContent = `İşleniyor · %${percent}`;
    }
  }

  if (text !== undefined && text !== null) {
    transcriptText.value = text;
    transcriptText.scrollTop = transcriptText.scrollHeight;
    updateTranscriptVisualState();

    if (window.TranskriptMotion) {
      window.TranskriptMotion.notifyTranscriptSettle(text.length);
    }
  }

  if (percent >= 100) {
    resetStateAfterCompletion();
  }
};

// Python tarafından evaluate_js ile çağrılan global fonksiyon: onTranscriptionError
window.onTranscriptionError = function(errorMsg) {
  showError("Transkripsiyon hatası: " + errorMsg);
  resetStateAfterCompletion();
};

function resetStateAfterCompletion() {
  isTranscribing = false;
  btnSelectFile.disabled = false;
  btnTranscribe.disabled = false;
  const btnLabel = btnTranscribe.querySelector(".btn-label-text") || btnTranscribe;
  btnLabel.textContent = "Metne Dönüştür";

  if (customTermsInput) {
    customTermsInput.disabled = false;
  }
  updateTranscriptVisualState();
}

// Kopyala Butonu Olayı
btnCopy.addEventListener("click", () => {
  const text = transcriptText.value;
  if (!text) return;

  const copyLabel = btnCopy.querySelector(".copy-text-label") || btnCopy;
  const originalText = copyLabel.textContent;

  navigator.clipboard.writeText(text).then(() => {
    copyLabel.textContent = "Kopyalandı ✓";
    btnCopy.classList.add("copied");
    setTimeout(() => {
      copyLabel.textContent = originalText;
      btnCopy.classList.remove("copied");
    }, 2000);
  }).catch(() => {
    // Fallback: execCommand
    transcriptText.select();
    document.execCommand("copy");
    copyLabel.textContent = "Kopyalandı ✓";
    btnCopy.classList.add("copied");
    setTimeout(() => {
      copyLabel.textContent = originalText;
      btnCopy.classList.remove("copied");
    }, 2000);
  });
});

// Bilgi & Gizlilik Çekmece Mantığı (Drawer Toggles)
const btnToggleWorkflow = document.getElementById("btnToggleWorkflow");
const btnTogglePrivacy = document.getElementById("btnTogglePrivacy");
const panelWorkflow = document.getElementById("panelWorkflow");
const panelPrivacy = document.getElementById("panelPrivacy");

function closeAllDrawers() {
  if (panelWorkflow) panelWorkflow.classList.add("hidden");
  if (panelPrivacy) panelPrivacy.classList.add("hidden");
  if (btnToggleWorkflow) {
    btnToggleWorkflow.classList.remove("active-pill");
    btnToggleWorkflow.setAttribute("aria-expanded", "false");
  }
  if (btnTogglePrivacy) {
    btnTogglePrivacy.classList.remove("active-pill");
    btnTogglePrivacy.setAttribute("aria-expanded", "false");
  }
}

if (btnToggleWorkflow && panelWorkflow) {
  btnToggleWorkflow.addEventListener("click", () => {
    const isCurrentlyHidden = panelWorkflow.classList.contains("hidden");
    closeAllDrawers();
    if (isCurrentlyHidden) {
      panelWorkflow.classList.remove("hidden");
      btnToggleWorkflow.classList.add("active-pill");
      btnToggleWorkflow.setAttribute("aria-expanded", "true");
    }
  });
}

if (btnTogglePrivacy && panelPrivacy) {
  btnTogglePrivacy.addEventListener("click", () => {
    const isCurrentlyHidden = panelPrivacy.classList.contains("hidden");
    closeAllDrawers();
    if (isCurrentlyHidden) {
      panelPrivacy.classList.remove("hidden");
      btnTogglePrivacy.classList.add("active-pill");
      btnTogglePrivacy.setAttribute("aria-expanded", "true");
    }
  });
}

// Çekmece Kapatma Butonları (✕)
document.querySelectorAll(".drawer-close-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetId = btn.getAttribute("data-target");
    if (targetId) {
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("hidden");
      if (targetId === "panelWorkflow" && btnToggleWorkflow) {
        btnToggleWorkflow.classList.remove("active-pill");
        btnToggleWorkflow.setAttribute("aria-expanded", "false");
      } else if (targetId === "panelPrivacy" && btnTogglePrivacy) {
        btnTogglePrivacy.classList.remove("active-pill");
        btnTogglePrivacy.setAttribute("aria-expanded", "false");
      }
    } else {
      closeAllDrawers();
    }
  });
});

