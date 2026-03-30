if (window.location.pathname === "/challenges") {
  const container = document.querySelector('.row > .col-md-12');

  if (container && !document.querySelector('#btn-unblock-page')) {
    // Create the unblock button
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
    span.innerText = (window.RemoverI18n ? RemoverI18n.t('btn_request_unblock') : "Request a challenge unblock");

    button.appendChild(icon);
    button.appendChild(span);
    wrapper.appendChild(button);
    container.prepend(wrapper);

    // Inject base CSS styles
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

  // Check whether challenge highlighting is enabled
  fetch('/api/v1/attempts_remover/config', {
    credentials: 'same-origin'
  })
  .then(response => response.json())
  .then(config => {
    if (config.highlight_blocked_challenges) {
      // Inject styles for blocked challenge buttons
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

      // State variables for cache and debounce optimisation
      let blockedChallengesCache = [];
      let lastBlockedUpdate = 0;
      let lastChallengeCount = 0;
      let markedButtons = new Set();
      let debounceTimer = null;

      // Mark blocked challenges with visual styling (uses a cache to minimise API calls)
      function markBlockedChallenges(forceRefresh = false) {
        const currentTime = Date.now();
        const currentButtons = document.querySelectorAll('[data-challenge-name], .challenge-button, .btn');
        const currentCount = currentButtons.length;

        // Refresh the blocked-list if:
        // 1. A forced refresh was requested
        // 2. More than 60 seconds have passed since the last update
        // 3. The number of visible challenge buttons changed
        const shouldRefreshData = forceRefresh ||
                                 (currentTime - lastBlockedUpdate) > 60000 ||
                                 currentCount !== lastChallengeCount;

        if (shouldRefreshData) {
          fetch('/api/v1/attempts_remover/blocked', {
            credentials: 'same-origin'
          })
          .then(response => response.json())
          .then(blockedChallenges => {
            blockedChallengesCache = blockedChallenges || [];
            lastBlockedUpdate = currentTime;
            lastChallengeCount = currentCount;
            markedButtons.clear(); // Reset the marked-buttons cache
            applyBlockedStyling();
          })
          .catch(e => {
            console.log('Info: No blocked challenges detected');
            blockedChallengesCache = [];
            lastBlockedUpdate = currentTime;
          });
        } else {
          // Serve from cache
          applyBlockedStyling();
        }
      }

      // Apply the blocked class to matching challenge buttons (separated for cache reuse)
      function applyBlockedStyling() {
        if (blockedChallengesCache.length === 0) return;

        const challengeButtons = document.querySelectorAll('[data-challenge-name], .challenge-button, .btn');
        
        challengeButtons.forEach(btn => {
          const btnText = btn.textContent || btn.innerText;
          const btnId = btn.getAttribute('data-challenge-id');
          const buttonKey = `${btnId || 'no-id'}-${btnText.trim()}`;
          
          // Skip buttons already processed in this pass
          if (markedButtons.has(buttonKey)) return;

          blockedChallengesCache.forEach(challenge => {
            const challengeName = challenge.challenge_name.trim();
            const buttonText = btnText.trim();
            const isExactMatch = buttonText === challengeName || 
                                buttonText.startsWith(challengeName + ' ') ||
                                buttonText.startsWith(challengeName + '\n');

            if (isExactMatch || parseInt(btnId, 10) === challenge.challenge_id) {
              btn.classList.add('blocked');
              btn.title = (window.RemoverI18n ? RemoverI18n.t('challenge_locked_tooltip', { current: challenge.fail_count, max: challenge.max_attempts }) : `\uD83D\uDD12 Challenge locked (${challenge.fail_count}/${challenge.max_attempts} attempts)`);
              markedButtons.add(buttonKey);
            }
          });
        });
      }

      // Debounced wrapper to avoid redundant calls during rapid DOM mutations
      function debouncedMarkBlocked() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          markBlockedChallenges();
        }, 1000); // 1 seconde de debounce
      }

      // Initial pass after the challenge list has had time to render
      setTimeout(() => markBlockedChallenges(true), 1000);

      // Observe DOM mutations and re-mark only when relevant challenge elements are added
      const observer = new MutationObserver((mutations) => {
        // Check whether any added node is (or contains) a challenge button
        const relevantChange = mutations.some(mutation => {
          return Array.from(mutation.addedNodes).some(node => {
            if (node.nodeType !== Node.ELEMENT_NODE) return false;
            
            // Check whether the added node is or contains a challenge button
            return node.classList?.contains('challenge-button') ||
                   node.querySelector?.('.challenge-button') ||
                   node.classList?.contains('btn') ||
                   node.querySelector?.('.btn') ||
                   node.getAttribute?.('data-challenge-name') ||
                   node.querySelector?.('[data-challenge-name]');
          });
        });

        if (relevantChange) {
          // console.log('Relevant change detected, marking blocked challenges...');
          debouncedMarkBlocked();
        }
      });

      observer.observe(document.body, { 
        childList: true, 
        subtree: true,
        attributes: false, 
        characterData: false 
      });

      // Force a refresh whenever the window regains focus (user switches back to the tab)
      window.addEventListener('focus', () => {
        markBlockedChallenges(true);
      });

        }
  })
  .catch(e => console.log('Config not loaded'));
}