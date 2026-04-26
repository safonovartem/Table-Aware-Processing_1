# Как пользоваться
## Шаг первый - выгрузка
![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_6.png)
К сожалению у меня так и не получилось сделать рабочий скрипт или exe файл. Нужно весь этот код выгрузить себе в IDE и там запустить 

## Шаг второй - перейдите на сайт с интерфейсом
![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_91.png)
Из-за того, чтобы в качестве веб интерфейса был использован Swagger, то можно удивиться такому обилию кнопок. Но нас интересуют лишь несколько из них

Для начала нажмите на Post, чтобы открыть наше окно
![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_1.png)

Теперь нажмите на кнопку Try it out

![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_2.png)

В появихшихся окнах загрузите файл с данными
Также вы можете настороить максимальный размер строк в чанке и установить ограничение для слишком широких таблиц

Когда всё загружино и настроено, нажмите кнопку "Execute"

**Важно!**
Процесс конвертации может сильно отличаться в зависимости от размера таблицы и кол-ва вашей оперативной памяти от несокльких секунд, до нескольких минут
Если страница не вылетела и не выдала ошибку, значит всё работает
![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_3.png)
Если всё прошло успешно, что на выходе вы получите JSON файл, чтобы его скачать нажмите "Download"
![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_4.png)
Поздравяю! Файл получен и скачен
![](https://github.com/safonovartem/Table-Aware-Processing/blob/master/Screenshot_5.png)


# Документация контракта JSON
| Поле в JSON | Тип | Описание |
| :--- | :--- | :--- |
| `profile` | Object | Профиль текущего листа таблицы. |
| `profile.dimensions` | Object | Размеры: `row_count` и `column_count`. |
| `profile.warnings` | Array | Массив предупреждений (например, "Много пустых строк"). |
| `profile.columns` | Array | Массив объектов с описанием каждой колонки (индекс, имя, тип, % пропусков, статистика). |
| `chunks` | Array | Массив сгенерированных чанков для индексации. |
| `chunks[].chunk_id` | String | Уникальный идентификатор чанка (например, `Sheet_rows_2_50`). |
| `chunks[].context` | Object | Метаданные источника (файл, лист, диапазоны `row_start`, `row_end`, `source_ref`). |
| `chunks[].text_projection`| String | Готовый Markdown-текст с шапкой и данными для векторной базы. |
