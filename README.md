# CTFD-Attempts-Remover

**CTFD-Attempts-Remover** is a plugin for [CTFd](https://ctfd.io) that lets teams request an **attempt reset** on a specific challenge directly from the CTFd interface — no more private messages or Discord pings to ask for a reset!

---

## What's New in V3

- **Multi-language i18n system** (FR / EN)
- **Code security hardening** — CSRF fixes, SSRF protection on Discord webhooks, input validation
- **UI improvements** — full Dark / Light mode support for CTFd and other style enhancements
- **Discord notifications** — a message is sent to a configurable Discord webhook whenever a team submits an unblock request, manageable from the plugin's admin panel

---

## Key Features

- **Built-in unblock request** — teams can submit a request to remove their failed attempts on a given challenge.
- **Challenge exclusion** — certain challenges can be excluded from the unblock system.
- **Blocked challenge highlighting** — locked challenges are visually flagged on the challenge board.
- **Single extra attempt** — teams can request one additional attempt instead of a full reset.
- **Configurable penalty system** for event administrators:
  - **Fixed penalty** — deducts a set number of points on unblock.
  - **Proportional penalty** — deducts a percentage of the challenge's point value.
- **Intuitive admin interface**:
  - Centralised view of all pending requests.
  - One-click approval.
  - Automatic penalty application.
  - Penalty type configuration.
  - Discord webhook configuration and test button.

---

## Why This Plugin?

> "Could you reset our attempts on the challenge 'TocTocToc', please?"

With this plugin, teams no longer need to go through Discord or send private messages to request an attempt reset. They can submit the request directly from the CTFd platform, and the admin panel provides a full management dashboard to review requests, approve actions, and apply penalties in one click.

Everyone benefits: players stay focused on the game, and the organising team is freed from repetitive manual tasks.

---

## Installation

1. Clone this repository into the `CTFd/plugins` folder:

   ```bash
   cd /path/to/CTFd/plugins
   git clone https://github.com/HACK-OLYTE/CTFD-Attempts-Remover.git
   ```

2. Restart your CTFd instance to load the plugin.

---

## Configuration

Go to **Admin Panel > Plugins > Attempts-Remover** to:

- Enable or disable the plugin (set penalties to 0 to effectively disable it).
- Choose the penalty type (fixed or proportional).
- Review and approve team requests.
- Configure the Discord webhook for notifications.

Demo video:

https://github.com/user-attachments/assets/90450a01-5411-4d25-ae22-b18eca2f2ff0

---

## Requirements

- CTFd ≥ v3.x
- Compatible with Docker and local installations.
- An up-to-date browser with JavaScript enabled.

---

## Support

For any questions or issues, please open an [issue](https://github.com/votre-utilisateur/CTFD-Attempts-Remover/issues) or reach out via the Hack'olyte association website: [contact](https://hackolyte.fr/contact/).

---

## Contributing

Contributions are welcome!

- Report bugs
- Suggest new features
- Submit pull requests

---

## License

This plugin is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
Please do not remove the footer from any HTML file without prior authorisation from the Hack'olyte association.
