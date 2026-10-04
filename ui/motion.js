/**
 * ui/motion.js: Transkript Orijinal Sinematik Hareket ve Etkileşim Sistemi
 * 
 * Bu dosya Transkript için sıfırdan, bağımsız ve saf Vanilla JS ile yazılmıştır.
 * Üçüncü taraf kütüphane veya kısıtlı lisanslı kod kesinlikle içermez.
 */

(function () {
  'use strict';

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', function (e) {
    prefersReducedMotion = e.matches;
  });

  /**
   * Hero Ses Alanı Pointer-Aware Işık Takibi
   * Yalnızca ses sahnesi üzerinde son derece hafif radyal ışık oluşturur.
   */
  function setupPointerHighlight() {
    if (prefersReducedMotion) return;

    var heroCard = document.getElementById('audioHeroCard');
    if (!heroCard) return;

    heroCard.addEventListener('mousemove', function (e) {
      if (prefersReducedMotion) return;
      var rect = heroCard.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      heroCard.style.setProperty('--mouse-x', x + 'px');
      heroCard.style.setProperty('--mouse-y', y + 'px');
    });

    heroCard.addEventListener('mouseleave', function () {
      heroCard.style.setProperty('--mouse-x', '50%');
      heroCard.style.setProperty('--mouse-y', '50%');
    });
  }

  /**
   * Buton Fiziksel Basış Sönümlemesi (Tactile Scale Feedback)
   */
  function setupTactileButtons() {
    if (prefersReducedMotion) return;

    var buttons = document.querySelectorAll('.btn');
    buttons.forEach(function (btn) {
      btn.addEventListener('pointerdown', function () {
        if (!btn.disabled) {
          btn.style.setProperty('--press-scale', '0.972');
        }
      });

      var release = function () {
        btn.style.setProperty('--press-scale', '1');
      };

      btn.addEventListener('pointerup', release);
      btn.addEventListener('pointerleave', release);
      btn.addEventListener('pointercancel', release);
    });
  }

  /**
   * Yeni Metin Ulaştığında Yumuşak Yerleşme Mikro-Geri Bildirimi
   */
  var lastTextLength = 0;
  function notifyTranscriptSettle(currentLength) {
    if (prefersReducedMotion) return;
    if (currentLength > lastTextLength && currentLength > 0) {
      var textarea = document.getElementById('transcriptText');
      if (textarea) {
        textarea.classList.remove('settle-pulse');
        void textarea.offsetWidth; // Reflow tetikle
        textarea.classList.add('settle-pulse');
      }
      lastTextLength = currentLength;
    }
  }

  window.TranskriptMotion = {
    isReducedMotion: function () {
      return prefersReducedMotion;
    },
    setupPointerHighlight: setupPointerHighlight,
    setupTactileButtons: setupTactileButtons,
    notifyTranscriptSettle: notifyTranscriptSettle
  };

  document.addEventListener('DOMContentLoaded', function () {
    setupPointerHighlight();
    setupTactileButtons();
  });
})();
