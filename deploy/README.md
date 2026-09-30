# Установка на VPN-сервер

Серверный режим запускает API и собранный frontend одним процессом на
`127.0.0.1:8000`. Чтение Docker и вызов root-owned helper выполняются локально,
без SSH-соединения сервера с самим собой. Существующий SSH-режим сохранён.
Служба работает от root, поскольку доступ к Docker и helper требует этих прав.
Не публикуйте порт через firewall или reverse proxy: внешней авторизации нет.

Размещаются:

- исходники и `frontend/dist` в `/opt/amnezia-panel/releases/<revision>`;
- ссылка `/opt/amnezia-panel/current` на выбранный выпуск;
- виртуальное окружение `/opt/amnezia-panel/venv`;
- `remote_helper.py`, `mutation_core.py`, `enroll_helper.py` в `/opt/amnezia-control`;
- policy и приватные резервные копии в `/var/lib/amnezia-control`;
- служба из `amnezia-panel.service`.

Перед установкой сохраните VPN-конфиг, clientsTable и runtime в приватный backup.
Перед обновлением дополнительно сохраните current, helper, policy и unit.
Установка helper и enrollment сами по себе peer-ы не меняют.
Enrollment выполняется только для реально установленного протокола:

```bash
python3 /opt/amnezia-control/enroll_helper.py --endpoint YOUR_PUBLIC_IP --protocol awg
```

Для первой установки на сервер с AWG после подготовки резервной копии,
распаковки исходников и собранного frontend в каталог выпуска:

```bash
bash /opt/amnezia-panel/releases/REV/deploy/install-server.sh /opt/amnezia-panel/releases/REV YOUR_PUBLIC_IP
```

Скрипт отказывается заменять уже установленную панель/помощник, проверяет порт,
устанавливает зависимости с проверкой хэшей и ожидает готовности API.

После установки зависимостей backend в venv и настройки current:

```bash
install -m 644 /opt/amnezia-panel/current/deploy/amnezia-panel.service /etc/systemd/system/amnezia-panel.service
systemctl daemon-reload
systemctl enable --now amnezia-panel
```

Открыть со своего компьютера:

```bash
ssh -N -L 8000:127.0.0.1:8000 root@YOUR_SERVER
```

Адрес: `http://127.0.0.1:8000`. Если локальный порт 8000 занят или зарезервирован,
используйте также разрешённый порт 5173:
`ssh -N -L 5173:127.0.0.1:8000 root@YOUR_SERVER`, затем откройте
`http://127.0.0.1:5173`. Произвольные другие порты не разрешены:
Host и Origin ограничены разрешёнными localhost-адресами.

На Ubuntu 24.04 при отсутствии `ensurepip` установите `python3.12-venv`
перед запуском установщика. Требуется Python 3.12+.

Приёмка: health, inventory, preflight, журнал, загрузка frontend; отсутствие
публичного listener на 8000; сохранность состава peer-ов и параметров интерфейса.
Создание/отзыв проверяются отдельно на собственном временном peer-е.
Официальные VPN-контейнеры не перезапускаются.

Откат первой установки: остановить и отключить только `amnezia-panel.service`.
Существующие VPN-подключения продолжат работать. Не удаляйте policy и журнал,
если через панель уже выполнялись операции. Для обновлений верните прежние
current/helper/unit и перезапустите только службу панели.
