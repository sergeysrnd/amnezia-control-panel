# Design specification

## Accepted concepts

- `docs/design/dashboard-concept.png` — primary dashboard at 1440×1024.
- `docs/design/create-connection-concept.png` — creation and one-time secret delivery state.

These generated concepts are the visual source of truth for the first implementation.

## Visible copy lock

Primary viewport: `AMN`, `Обзор`, `Клиенты`, `Журнал`, `Сервер`, server hostname, `Подключён`, `AWG Legacy`, `AWG 2.0` or `AWG 3.1`, `WireGuard`, `Подключения`, `Новое подключение`, table headings `Клиент`, `IP-адрес`, `Последнее подключение`, `Трафик`, `Endpoint`, `Статус`, footer `Только управление подключениями · Контейнеры не изменяются`.

Creation state: `Новое подключение`, `Имя клиента`, `Протокол`, `Следующий IP-адрес`, `Публичный endpoint`, `Добавить PersistentKeepalive 25`, one-time private-key notice, `Отмена`, `Создать подключение`. Success state: `Подключение создано`, `Скачать .conf`, `Скопировать vpn://`, one-time download warning.

## Tokens

- Background: true pale cool gray `#f4f6f9`.
- Surface: true white `#ffffff`.
- Text: graphite `#141820`; muted `#636b7a`.
- Accent: deep indigo `#273fbd`; selected surface `#f2f5ff`.
- Border: cool neutral `#dce1e8`.
- Semantic: green `#0aa457`, amber `#f0a000`, red `#e92d35`.
- Radius: 6–10 px; controls predominantly 7 px.
- Shadow: absent on application surfaces; only modal elevation.
- Typography: Inter-compatible system sans, 12–15 px chrome, 21–24 px headings.

## Container model

One app shell, open table surface, protocol rail, and one right inspector. No dashboard card grid. Modal is one frame split into a form and one-time delivery area.

## Icon inventory

Consistent outline icons at 1.75 px stroke: overview monitor, users, log document, refresh, add, close, copy, download, revoke, sort, validation check, warning. Icons use `currentColor`, rounded line caps and joins.

## Responsive behavior

- Under 1180 px the sidebar becomes an icon rail and inspector becomes an overlay drawer.
- Under 760 px navigation becomes a bottom bar; the table scrolls horizontally; inspector is full-width; creation modal becomes a full-height sheet.
- Content text and controls remain code-native at every breakpoint.
