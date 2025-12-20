if (window.location.pathname === "/challenges") {
  const container = document.querySelector('.row > .col-md-12');

  if (container && !document.querySelector('#btn-unblock-page')) {
    // Création du bouton (toujours présent)
    const wrapper = document.createElement('div');
    wrapper.className = "d-flex justify-content-center mb-4";
    wrapper.id = "btn-unblock-wrapper";

    const button = document.createElement('a');
    button.href = "/plugins/ctfd-attempts-remover/unblock";
    button.className = "btn btn-info text-white shadow rounded-pill px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2 transition";
    button.id = "btn-unblock-page";

    const icon = document.createElement('i');
    icon.className = "fa fa-user-lock action-icon";

    const span = document.createElement('span');
    span.innerText = "Demander un déblocage challenge";

    button.appendChild(icon);
    button.appendChild(span);
    wrapper.appendChild(button);
    container.prepend(wrapper);

    // Style CSS de base (toujours présent)
    if (!document.querySelector('#custom-unblock-style')) {
      const style = document.createElement('style');
      style.id = 'custom-unblock-style';
      style.innerHTML = `
        .transition {
          transition: all 0.2s ease-in-out;
        }
        #btn-unblock-page:hover {
          background-color: #212529;
        }
      `;
      document.head.appendChild(style);
    }
  }

  // Vérifier si le surlignage est activé
  fetch('/api/v1/attempts_remover/config', {
    credentials: 'same-origin'
  })
  .then(response => response.json())
  .then(config => {
    if (config.highlight_blocked_challenges) {
      // Ajouter les styles pour les challenges bloqués
      const blockedStyle = document.createElement('style');
      blockedStyle.id = 'blocked-challenges-style';
      blockedStyle.innerHTML = `
        .challenge-button.blocked {
          background: linear-gradient(135deg, #dc3545, #c82333) !important;
          border-color: #dc3545 !important;
          position: relative;
          overflow: hidden;
        }

        .challenge-button.blocked::before {
          content: "🔒";
          position: absolute;
          top: 5px;
          left: 8px;
          font-size: 12px;
          z-index: 10;
        }

        .challenge-button.blocked:hover {
          background: linear-gradient(135deg, #c82333, #bd2130) !important;
          transform: scale(1.02);
          box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
        }

        .challenge-button.blocked {
          animation: subtle-pulse 3s ease-in-out infinite;
        }

        @keyframes subtle-pulse {
          0%, 100% { box-shadow: 0 2px 8px rgba(220, 53, 69, 0.3); }
          50% { box-shadow: 0 4px 16px rgba(220, 53, 69, 0.5); }
        }
      `;
      document.head.appendChild(blockedStyle);

      // Variables pour l'optimisation
      let blockedChallengesCache = [];
      let lastBlockedUpdate = 0;
      let lastChallengeCount = 0;
      let markedButtons = new Set();
      let debounceTimer = null;

      // Fonction pour marquer les challenges bloqués (optimisée)
      function markBlockedChallenges(forceRefresh = false) {
        const currentTime = Date.now();
        const currentButtons = document.querySelectorAll('[data-challenge-name], .challenge-button, .btn');
        const currentCount = currentButtons.length;
        
        // Conditions pour recharger les données :
        // 1. Force refresh demandé
        // 2. Plus de 60 secondes depuis la dernière maj
        // 3. Nombre de challenges a changé
        const shouldRefreshData = forceRefresh || 
                                 (currentTime - lastBlockedUpdate) > 60000 || 
                                 currentCount !== lastChallengeCount;

        if (shouldRefreshData) {
          // console.log('Rechargement des challenges bloqués...', {
          //   forceRefresh,
          //   timeSince: currentTime - lastBlockedUpdate,
          //   countChanged: currentCount !== lastChallengeCount
          // });

          fetch('/api/v1/attempts_remover/blocked', {
            credentials: 'same-origin'
          })
          .then(response => response.json())
          .then(blockedChallenges => {
            blockedChallengesCache = blockedChallenges || [];
            lastBlockedUpdate = currentTime;
            lastChallengeCount = currentCount;
            markedButtons.clear(); // Reset le cache des boutons marqués
            applyBlockedStyling();
          })
          .catch(e => {
            console.log('Info: Pas de challenges bloqués détectés');
            blockedChallengesCache = [];
            lastBlockedUpdate = currentTime;
          });
        } else {
          // Utiliser le cache
          applyBlockedStyling();
        }
      }

      // Fonction pour appliquer le style aux boutons (séparée pour réutilisation)
      function applyBlockedStyling() {
        if (blockedChallengesCache.length === 0) return;

        const challengeButtons = document.querySelectorAll('[data-challenge-name], .challenge-button, .btn');
        
        challengeButtons.forEach(btn => {
          const btnText = btn.textContent || btn.innerText;
          const btnId = btn.getAttribute('data-challenge-id');
          const buttonKey = `${btnId || 'no-id'}-${btnText.trim()}`;
          
          // Éviter de retraiter le même bouton
          if (markedButtons.has(buttonKey)) return;

          blockedChallengesCache.forEach(challenge => {
            const challengeName = challenge.challenge_name.trim();
            const buttonText = btnText.trim();
            const isExactMatch = buttonText === challengeName || 
                                buttonText.startsWith(challengeName + ' ') ||
                                buttonText.startsWith(challengeName + '\n');

            if (isExactMatch || btnId == challenge.challenge_id) {
              btn.classList.add('blocked');
              btn.title = `🔒 Challenge bloqué (${challenge.fail_count}/${challenge.max_attempts} tentatives)`;
              markedButtons.add(buttonKey);
            }
          });
        });
      }

      // Fonction avec debounce pour éviter les appels multiples
      function debouncedMarkBlocked() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          markBlockedChallenges();
        }, 1000); // 1 seconde de debounce
      }

      // Marquer les challenges bloqués au chargement
      setTimeout(() => markBlockedChallenges(true), 1000);

      // Observer optimisé - ne réagit que si nécessaire
      const observer = new MutationObserver((mutations) => {
        // Vérifier si des éléments pertinents ont été ajoutés
        const relevantChange = mutations.some(mutation => {
          return Array.from(mutation.addedNodes).some(node => {
            if (node.nodeType !== Node.ELEMENT_NODE) return false;
            
            // Vérifier si c'est un challenge button ou contient des challenge buttons
            return node.classList?.contains('challenge-button') ||
                   node.querySelector?.('.challenge-button') ||
                   node.classList?.contains('btn') ||
                   node.querySelector?.('.btn') ||
                   node.getAttribute?.('data-challenge-name') ||
                   node.querySelector?.('[data-challenge-name]');
          });
        });

        if (relevantChange) {
          // console.log('Changement pertinent détecté, marking blocked challenges...');
          debouncedMarkBlocked();
        }
      });

      observer.observe(document.body, { 
        childList: true, 
        subtree: true,
        attributes: false, 
        characterData: false 
      });

      // Événements pour forcer le refresh
      window.addEventListener('focus', () => {
        // Refresh quand la fenêtre reprend le focus (utilisateur revient)
        markBlockedChallenges(true);
      });

      // Fonction de debug
      window.attemptsRemoverDebug = function() {
        console.log('📊 État attempts-remover:', {
          cacheSize: blockedChallengesCache.length,
          markedButtons: markedButtons.size,
          lastUpdate: new Date(lastBlockedUpdate).toLocaleTimeString(),
          timeSinceUpdate: Date.now() - lastBlockedUpdate,
          currentButtons: document.querySelectorAll('[data-challenge-name], .challenge-button, .btn').length
        });
      };
    }
  })
  .catch(e => console.log('Config non chargée'));
}