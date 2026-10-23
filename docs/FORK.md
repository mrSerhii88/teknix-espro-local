# Maintained ESPRO-15 fork

## Українською

Це fork інтеграції [Vitalii Kovalenko](https://github.com/vitaliy-kovalenko/teknix-espro-local),
на базі upstream `v0.1.2` (commit `02e195b67d7f351d43f6b11bbd1d4fd00484cc92`).
Авторство та ліцензія MIT збережені.

### Область підтримки

**Цей реліз — тільки для перевіреного ESPRO-15 з шістьма ступенями по 2,5 кВт.**
Не встановлюйте його на ESPRO-12, іншу потужність чи неперевірену апаратну ревізію:
помилкове масштабування може задати завелику потужність. Це не універсальний
автоматичний визначник моделі.

### Виправлення

* P4 (опалення) і P5 (ГВП): діапазон 2,5–15 кВт, крок 2,5 кВт, кодування 1–6 реле.
  Значення поза діапазоном або між ступенями відхиляються до надсилання команди.
* P6: ліміт пріоритетного споживача відображається як кількість реле × 2,5 кВт.
* Watchdog: якщо понад 90 секунд не отримано коректний INFO-кадр, координатор
  переводить сутності в `unavailable`. Перевірка — кожні 10 секунд, тому фактичне
  виявлення займає приблизно 90–100 секунд після останнього коректного кадру.
  Пошкоджені кадри не поновлюють термін; наступний коректний кадр відновлює доступність.
* Домен `teknix_espro_local`, ключі сутностей та унікальні ідентифікатори не змінені.
  Наявні сутності, пристрої та автоматизації не потрібно створювати заново.

Watchdog **не є апаратним захистом і сам не зупиняє котел**. При втраті зв'язку
дистанційне вимкнення не гарантоване. Захист від перегріву, витоку струму та проблем
циркуляції має забезпечувати котел і електрична інсталяція. Домашні сценарії HA
мають окремо обробляти `unavailable` та перевіряти підтвердження команд.

### Встановлення та перехід з upstream

1. Зробіть повну резервну копію HA та завантажте її на інший пристрій.
2. Переконайтеся, що опалення вимкнене. Не видаляйте пристрій/інтеграцію Teknix
   зі **Settings → Devices & services** — це не потрібно для заміни джерела коду.
3. Джерело для HACS: `https://github.com/mrSerhii88/teknix-espro-local`, тип Integration.
   Встановлюйте опублікований реліз цього fork, а не upstream-реліз.
4. Обидва репозиторії використовують одну папку `custom_components/teknix_espro_local`.
   Не керуйте двома встановленими копіями одночасно. Якщо HACS повідомляє про конфлікт,
   спочатку збережіть копію папки та приберіть старий запис **тільки з HACS**.
   Перевіряйте діалог видалення: не погоджуйтеся на втрату єдиної робочої копії.
   Після цього встановіть fork; налаштування в Devices & services залишайте незмінними.
5. Перезапустіть HA, перевірте версію, доступність, крок 2,5 кВт і реальне підтвердження
   ON/OFF. Короткий нагрів тестуйте на мінімальній потужності та за наявності мережі.
6. Якщо HACS не дозволяє безпечно переключити джерело, залиште чинну інтеграцію
   й використайте ручне встановлення релізу поверх тієї самої папки після резервування.
   Не редагуйте внутрішню `.storage` вручну.

### Підтримка оновлень

* Оновлення самого HACS не є оновленням цього fork.
* Встановлення/Redownload upstream замінить наші зміни. Перед встановленням завжди
  перевіряйте власника репозиторію та примітки релізу.
* Нові версії upstream не зливаються автоматично. Спочатку отримайте зміни у
  робочу гілку fork, перегляньте diff, перенесіть виправлення і запустіть тести.
* Не змінюйте домен і ключі/unique_id сутностей при звичайному оновленні.
* Випускайте новий тег/реліз лише після тестів. Оновлення HA Core також може
  змінити API — fork не гарантує сумісності з будь-якими майбутніми версіями HA.
* Для відкату встановіть попередній реліз **цього fork** або відновіть перевірену
  резервну копію. Після відкату перевірте налаштування на самому котлі.

### Перевірки

```sh
python -m unittest discover -s tests -v
python -m compileall -q custom_components tests
```

Тести офлайн: шість ступенів P4/P5, некоректні значення, P6, номінальна потужність,
I0/I1, checksum, індекси команд, старіння телеметрії, відновлення зв'язку і очищення
таймера. Вони не підключаються до MQTT, не надсилають команд і не замінюють тесту
реальної інсталяції. HACS і Hassfest перевіряються окремими GitHub Actions.

На ESPRO-15 перевірено реальне ввімкнення/вимкнення головного вимикача та опалення,
зміну/відновлення уставок, ступінь 2,5 кВт і повернення станів після перезапуску HA.
Усі шість ступенів перевірено програмно; фізичного навантажувального тесту на 15 кВт
і випробування аварій перегріву/витоку/втрати циркуляції не проводилося.

Репозиторій містить код, документацію та синтетичні тестові дані — не домашні
`configuration.yaml`, `automations.yaml`, ключі, MQTT-паролі чи історію подій.

## English summary

This is a maintained, MIT-licensed fork of upstream v0.1.2 specifically for the
tested six-stage **Teknix ESPRO-15** hardware (2.5 kW per stage). It is not suitable
for ESPRO-12 or unverified models. Changes are P4/P5 power scaling and input
validation, P6 display scaling, and a valid-INFO-frame telemetry watchdog.

The MQTT poll remains 30 seconds. Cached entities become unavailable after more
than 90 seconds without valid data, checked every 10 seconds; valid frames recover
availability. This does not guarantee command delivery, measure actual heater
power, or replace hardware safety. Heating permission is not proof that heating
elements are drawing power; firmware startup delays may apply.

The integration domain, config-entry schema and entity keys/unique IDs remain
unchanged. Migrate the HACS source without deleting the HA config entry. Back up
first, do not install both sources concurrently, and restart HA after installing
a release. Review and test upstream changes before merging; no automatic
upstream synchronization is configured. The offline tests use synthetic data and
lightweight coordinator stubs, not a complete Home Assistant runtime.
