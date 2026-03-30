/**
 * RemoverI18n - Internationalization for the Attempts Remover plugin
 * Supports: English (en), French (fr)
 * Default: English
 * Pattern inspired by CampI18n (CTFD-plugin-camp)
 */
var RemoverI18n = (function () {

    var translations = {
        en: {
            /* --- settingsremover.js --- */
            btn_request_unblock:      'Request a challenge unblock',
            challenge_locked_tooltip: '\uD83D\uDD12 Challenge locked ({current}/{max} attempts)',

            /* --- shared --- */
            refresh:       'Refresh',
            loading:       'Loading...',
            sending:       'Sending...',
            error:         'Error',
            network_error: 'Network error',
            error_prefix:  'Error: ',

            /* --- user unblock page (static HTML) --- */
            header_title:             'Unblock Center',
            header_subtitle:          'Manage your blocked challenges',
            back_to_challenges:       'Back to challenges',
            loading_config:           'Loading configuration...',
            tab_blocked:              'Blocked Challenges',
            tab_history:              'History',
            blocked_section_title:    'Currently blocked challenges',
            processed_requests_title: 'Processed requests',

            /* --- user unblock page (JS) --- */
            penalty_fixed:       'Full unblock costs {cost} points',
            penalty_percent:     'Cost is {pct}% of challenge points',
            penalty_warning:     '\u26A0\uFE0F Warning: point losses from each unblock are cumulative and deducted from your total score.',
            no_blocked:          'No blocked challenges',
            all_accessible:      'You can access all challenges!',
            attempts_label:      'Attempts: {current} / {max}',
            status_in_progress:  'In progress',
            status_blocked:      'Blocked',
            cost_full_unblock:   'Full unblock: {cost}',
            cost_single_attempt: '1 extra attempt: {cost}',
            btn_full_pending:    'Full unblock request being processed',
            btn_single_pending:  'Extra attempt request being processed',
            btn_full_unblock:    'Full unblock',
            btn_single_attempt:  'Get 1 attempt',
            request_sent:        'Request sent! Refreshing...',
            loading_error:       'Loading error',
            error_load_data:     'Could not load data. Please try again.',
            retry:               'Retry',
            history_empty:            'No processed requests yet',
            history_col_challenge:    'Challenge',
            history_col_processed_by: 'Processed by',
            history_col_type:         'Type',
            history_col_cost:         'Cost',
            history_col_processed_on: 'Processed on',
            type_full_unblock:   'Full unblock',
            type_single_attempt: 'Single attempt',
            total_cost:          'In total, your unblocks have cost you {total} points!',
            history_load_error:  'Error loading history',

            /* --- admin page (static HTML) --- */
            admin_subtitle:           'Advanced challenge unblock management',
            stat_blocked_teams:       'Blocked Teams',
            stat_pending_requests:    'Pending requests',
            stat_excluded_challenges: 'Excluded challenges',
            stat_total_unblocks:      'Total unblocks',
            tab_config:               'Configuration',
            tab_blocked_admin:        'Blocked Teams',
            tab_exclusions:           'Excluded Challenges',
            tab_history_admin:        'History',
            config_title:             'Penalty Configuration',
            loading_config_admin:     'Loading configuration...',
            config_mode_label:        'Penalty mode',
            mode_fixed:               'Fixed cost',
            mode_percent:             'Percentage',
            config_fixed_cost_label:  'Fixed cost (points)',
            config_percent_cost_label:'Challenge percentage',
            btn_save_config:          'Save configuration',
            single_attempt_title:     'Extra Attempt Configuration',
            label_enable_feature:     'Enable feature',
            disabled:                 'Disabled',
            enabled:                  'Enabled',
            label_cost_mode:          'Cost mode',
            label_highlight_blocked:  'Highlight blocked challenges',
            btn_save_this_config:     'Save this configuration',
            discord_title:            'Discord Notifications',
            discord_info:             'A message will be sent to Discord on each team unblock request. Leave empty to disable.',
            label_webhook_url:        'Discord Webhook URL',
            label_role_id:            'Role ID to ping',
            label_role_id_optional:   '(optional)',
            btn_save_discord:         'Save Discord configuration',
            btn_test:                 'Test',
            blocked_teams_title:      'Currently blocked teams',
            excluded_blocked_title:   'Blocked on excluded challenges',
            excluded_blocked_subtitle:'These teams are blocked on challenges excluded from the unblock system.',
            search_team_placeholder:  'Search a team...',
            exclude_title:            'Exclude a challenge',
            select_challenge_label:   'Select a challenge',
            btn_exclude:              'Exclude this challenge',
            excluded_list_title:      'Excluded challenges',
            history_title:            'Unblock history',
            loading_logs:             'Loading logs...',

            /* --- admin page (JS) --- */
            current_config_label:     'Current configuration: ',
            mode_fixed_desc:          'Fixed mode \u2014 {cost} points per unblock',
            mode_percent_desc:        'Percentage mode \u2014 {pct}% of challenge points',
            no_blocks_detected:       'No blocks detected',
            all_teams_access:         'All teams can access their challenges!',
            table_team:               'Team',
            table_challenge:          'Challenge',
            table_points:             'Points',
            table_attempts:           'Attempts',
            table_loss:               'Loss',
            table_block_date:         'Block date',
            table_requests:           'Requests',
            table_actions:            'Actions',
            badge_excluded:           'EXCLUDED',
            badge_excluded_tooltip:   'Challenge excluded from user unblock',
            badge_full_unblock:       'Full unblock',
            badge_single_attempt:     'Single attempt',
            badge_none:               'None',
            unknown_date:             'Unknown',
            btn_full_unblock_action:  'Full unblock',
            btn_single_attempt_action:'1 attempt',
            confirm_unblock:          'Confirm unblocking "{team}" for "{challenge}"?',
            unblock_success:          '{team} unblocked successfully (-{cost} pts)',
            error_unblocking:         'Error unblocking',
            confirm_grant_attempt:    'Grant an extra attempt to "{team}" for "{challenge}"?',
            grant_success:            '{team} received an extra attempt (-{cost} pts)',
            error_granting:           'Error granting attempt',
            no_recent_unblocks:       'No recent unblocks recorded',
            log_col_date:             'Date',
            log_col_admin:            'Admin',
            log_col_team:             'Team',
            log_col_challenge:        'Challenge',
            log_col_type:             'Type',
            log_type_full:            'Full',
            log_type_single:          '1 attempt',
            select_challenge_opt:     'Select a challenge...',
            excluded_subtitle:        '{value} pts \u2014 Excluded by {by}',
            btn_reinclude:            'Re-include',
            no_excluded:              'No excluded challenges',
            error_load_config:        'Error loading configuration',
            config_saved:             'Configuration saved successfully!',
            single_config_saved:      'Single attempt configuration saved!',
            discord_config_saved:     'Discord configuration saved!',
            test_sent:                'Test message sent to Discord!',
            error_saving:             'Error saving',
            error_load_challenges:    'Error loading challenges',
            error_load_exclusions:    'Error loading exclusions',
            error_reincluding:        'Error re-including challenge',
            error_load_blocked:       'Error loading blocked teams',
            error_load_logs:          'Error loading logs',
            confirm_exclude:          'Are you sure you want to exclude "{name}" from unblock requests?',
            reinclude_confirm:        'Re-include "{name}" in unblock requests?',
        },

        fr: {
            btn_request_unblock:      'Demander un d\u00e9blocage challenge',
            challenge_locked_tooltip: '\uD83D\uDD12 Challenge bloqu\u00e9 ({current}/{max} tentatives)',
            refresh:       'Actualiser',
            loading:       'Chargement...',
            sending:       'Envoi...',
            error:         'Erreur',
            network_error: 'Erreur r\u00e9seau',
            error_prefix:  'Erreur\u00a0: ',
            header_title:             'Centre de d\u00e9blocage',
            header_subtitle:          'Gestion de vos challenges bloqu\u00e9s',
            back_to_challenges:       'Retour aux challenges',
            loading_config:           'Chargement de la configuration...',
            tab_blocked:              'Challenges bloqu\u00e9s',
            tab_history:              'Historique',
            blocked_section_title:    'Challenges actuellement bloqu\u00e9s',
            processed_requests_title: 'Demandes trait\u00e9es',
            penalty_fixed:       'La r\u00e9cup\u00e9ration compl\u00e8te vous co\u00fbtera {cost} points',
            penalty_percent:     'Le co\u00fbt est de {pct}% des points du challenge',
            penalty_warning:     '\u26A0\uFE0F Attention\u00a0: les pertes de points li\u00e9es \u00e0 chaque d\u00e9blocage s\'additionnent et sont d\u00e9duites de votre score global.',
            no_blocked:          'Aucun challenge bloqu\u00e9',
            all_accessible:      'Vous pouvez acc\u00e9der \u00e0 tous les challenges\u00a0!',
            attempts_label:      'Vos tentatives\u00a0: {current} / {max}',
            status_in_progress:  'En cours',
            status_blocked:      'Bloqu\u00e9',
            cost_full_unblock:   'R\u00e9cup\u00e9rer toutes les tentatives\u00a0: {cost}',
            cost_single_attempt: 'R\u00e9cup\u00e9rer 1 tentative\u00a0: {cost}',
            btn_full_pending:    'Demande de d\u00e9blocage complet en cours de traitement',
            btn_single_pending:  'Demande de tentative suppl\u00e9mentaire en cours de traitement',
            btn_full_unblock:    'D\u00e9blocage complet',
            btn_single_attempt:  'R\u00e9cup\u00e9rer 1 tentative',
            request_sent:        'Demande envoy\u00e9e\u00a0! Actualisation...',
            loading_error:       'Erreur de chargement',
            error_load_data:     'Impossible de charger les donn\u00e9es. Veuillez r\u00e9essayer.',
            retry:               'R\u00e9essayer',
            history_empty:            'Aucune demande trait\u00e9e pour le moment',
            history_col_challenge:    'Challenge',
            history_col_processed_by: 'Trait\u00e9 par',
            history_col_type:         'Type',
            history_col_cost:         'Co\u00fbt',
            history_col_processed_on: 'Date de traitement',
            type_full_unblock:   'D\u00e9blocage complet',
            type_single_attempt: 'Tentative unique',
            total_cost:          'Au total, vos d\u00e9blocages vous ont co\u00fbt\u00e9 {total} points\u00a0!',
            history_load_error:  'Erreur lors du chargement de l\'historique',
            admin_subtitle:           'Gestion avanc\u00e9e des d\u00e9blocages de challenges',
            stat_blocked_teams:       '\u00c9quipes bloqu\u00e9es',
            stat_pending_requests:    'Demandes en attente',
            stat_excluded_challenges: 'Challenges exclus',
            stat_total_unblocks:      'D\u00e9blocages total',
            tab_config:               'Configuration',
            tab_blocked_admin:        '\u00c9quipes bloqu\u00e9es',
            tab_exclusions:           'Challenges exclus',
            tab_history_admin:        'Historique',
            config_title:             'Configuration du malus',
            loading_config_admin:     'Chargement de la configuration...',
            config_mode_label:        'Mode de malus',
            mode_fixed:               'Co\u00fbt fixe',
            mode_percent:             'Pourcentage',
            config_fixed_cost_label:  'Co\u00fbt fixe (points)',
            config_percent_cost_label:'Pourcentage du challenge',
            btn_save_config:          'Enregistrer la configuration',
            single_attempt_title:     'Configuration tentative suppl\u00e9mentaire',
            label_enable_feature:     'Activer la fonctionnalit\u00e9',
            disabled:                 'D\u00e9sactiv\u00e9',
            enabled:                  'Activ\u00e9',
            label_cost_mode:          'Mode de co\u00fbt',
            label_highlight_blocked:  'Surligner challenges bloqu\u00e9s',
            btn_save_this_config:     'Enregistrer cette configuration',
            discord_title:            'Notifications Discord',
            discord_info:             'Un message sera envoy\u00e9 sur Discord \u00e0 chaque demande de d\u00e9blocage. Laissez vide pour d\u00e9sactiver.',
            label_webhook_url:        'URL du Webhook Discord',
            label_role_id:            'ID du r\u00f4le \u00e0 pinger',
            label_role_id_optional:   '(optionnel)',
            btn_save_discord:         'Enregistrer la configuration Discord',
            btn_test:                 'Tester',
            blocked_teams_title:      '\u00c9quipes actuellement bloqu\u00e9es',
            excluded_blocked_title:   'Bloqu\u00e9s sur challenges exclus',
            excluded_blocked_subtitle:'Ces \u00e9quipes sont bloqu\u00e9es sur des challenges exclus du syst\u00e8me de d\u00e9blocage.',
            search_team_placeholder:  'Rechercher une \u00e9quipe...',
            exclude_title:            'Exclure un challenge',
            select_challenge_label:   'S\u00e9lectionner un challenge',
            btn_exclude:              'Exclure ce challenge',
            excluded_list_title:      'Challenges exclus',
            history_title:            'Historique des d\u00e9blocages',
            loading_logs:             'Chargement des logs...',
            current_config_label:     'Configuration actuelle\u00a0: ',
            mode_fixed_desc:          'Mode fixe \u2014 {cost} points par d\u00e9blocage',
            mode_percent_desc:        'Mode pourcentage \u2014 {pct}% des points du challenge',
            no_blocks_detected:       'Aucun blocage d\u00e9tect\u00e9',
            all_teams_access:         'Toutes les \u00e9quipes peuvent acc\u00e9der \u00e0 leurs challenges\u00a0!',
            table_team:               '\u00c9quipe',
            table_challenge:          'Challenge',
            table_points:             'Points',
            table_attempts:           'Tentatives',
            table_loss:               'Perte',
            table_block_date:         'Date blocage',
            table_requests:           'Demandes',
            table_actions:            'Actions',
            badge_excluded:           'EXCLU',
            badge_excluded_tooltip:   'Challenge exclu du d\u00e9blocage utilisateur',
            badge_full_unblock:       'D\u00e9blocage complet',
            badge_single_attempt:     'Tentative unique',
            badge_none:               'Aucune',
            unknown_date:             'Inconnue',
            btn_full_unblock_action:  'D\u00e9blocage complet',
            btn_single_attempt_action:'1 tentative',
            confirm_unblock:          'Confirmer le d\u00e9blocage de "{team}" pour "{challenge}"\u00a0?',
            unblock_success:          '{team} d\u00e9bloqu\u00e9e avec succ\u00e8s (-{cost} pts)',
            error_unblocking:         'Erreur lors du d\u00e9blocage',
            confirm_grant_attempt:    'Accorder une tentative suppl\u00e9mentaire \u00e0 "{team}" pour "{challenge}"\u00a0?',
            grant_success:            '{team} a re\u00e7u une tentative suppl\u00e9mentaire (-{cost} pts)',
            error_granting:           'Erreur lors de l\'attribution',
            no_recent_unblocks:       'Aucun d\u00e9blocage r\u00e9cent enregistr\u00e9',
            log_col_date:             'Date',
            log_col_admin:            'Admin',
            log_col_team:             '\u00c9quipe',
            log_col_challenge:        'Challenge',
            log_col_type:             'Type',
            log_type_full:            'Complet',
            log_type_single:          '1 tentative',
            select_challenge_opt:     'S\u00e9lectionner un challenge...',
            excluded_subtitle:        '{value} pts \u2014 Exclu par {by}',
            btn_reinclude:            'R\u00e9int\u00e9grer',
            no_excluded:              'Aucun challenge exclu',
            error_load_config:        'Erreur lors du chargement de la configuration',
            config_saved:             'Configuration enregistr\u00e9e avec succ\u00e8s\u00a0!',
            single_config_saved:      'Configuration des tentatives uniques enregistr\u00e9e\u00a0!',
            discord_config_saved:     'Configuration Discord enregistr\u00e9e\u00a0!',
            test_sent:                'Message de test envoy\u00e9 sur Discord\u00a0!',
            error_saving:             'Erreur lors de l\'enregistrement',
            error_load_challenges:    'Erreur lors du chargement des challenges',
            error_load_exclusions:    'Erreur lors du chargement des exclusions',
            error_reincluding:        'Erreur lors de la r\u00e9int\u00e9gration',
            error_load_blocked:       'Erreur lors du chargement des \u00e9quipes bloqu\u00e9es',
            error_load_logs:          'Erreur lors du chargement des logs',
            confirm_exclude:          '\u00cates-vous s\u00fbr de vouloir exclure "{name}" des demandes de d\u00e9blocage\u00a0?',
            reinclude_confirm:        'R\u00e9int\u00e9grer "{name}" dans les demandes de d\u00e9blocage\u00a0?',
        }
    };

    /**
     * Detect language from multiple sources, in priority order:
     *  1. window._remover_force_lang  (explicit override, used in admin page)
     *  2. <html lang="...">           (set by CTFd server-side — most reliable)
     *  3. Cookies: `language`, `locale`, `lang`
     *  4. navigator.languages         (browser preference)
     *  5. Fallback: 'en'
     */
    function getLang() {
        if (window._remover_force_lang && translations[window._remover_force_lang]) {
            return window._remover_force_lang;
        }
        // CTFd sets the <html lang="..."> attribute server-side based on the selected language
        var htmlLang = (document.documentElement.lang || '').split(/[-_]/)[0].toLowerCase();
        if (htmlLang && translations[htmlLang]) return htmlLang;

        var cookieNames = ['language', 'locale', 'lang'];
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var parts = cookies[i].trim().split('=');
            var name = parts[0].trim();
            if (cookieNames.indexOf(name) !== -1 && parts[1]) {
                var lang = decodeURIComponent(parts[1].trim()).split(/[-_]/)[0].toLowerCase();
                if (translations[lang]) return lang;
            }
        }
        var langs = navigator.languages || [navigator.language || navigator.userLanguage || 'en'];
        for (var j = 0; j < langs.length; j++) {
            var l = langs[j].split(/[-_]/)[0].toLowerCase();
            if (translations[l]) return l;
        }
        return 'en';
    }

    /**
     * Translate a key, with optional {placeholder} substitution.
     * Usage: t('key')  or  t('key').replace('{var}', value)
     * Also accepts a vars object: t('key', {var: value})
     */
    function t(key, vars) {
        var lang = getLang();
        var dict = translations[lang] || translations['en'];
        var str = dict[key] !== undefined ? dict[key] : (translations['en'][key] || key);
        if (vars) {
            for (var k in vars) {
                if (vars.hasOwnProperty(k)) {
                    str = str.split('{' + k + '}').join(vars[k]);
                }
            }
        }
        return str;
    }

    /**
     * Apply translations to all [data-i18n] and [data-i18n-placeholder] elements.
     */
    function apply() {
        document.querySelectorAll('[data-i18n]').forEach(function (el) {
            el.textContent = t(el.getAttribute('data-i18n'));
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
            el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
        });
        document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
            el.title = t(el.getAttribute('data-i18n-title'));
        });
    }

    /* Auto-apply on DOMContentLoaded — no manual call needed in templates */
    document.addEventListener('DOMContentLoaded', apply);

    return { t: t, apply: apply, getLang: getLang };

})();
