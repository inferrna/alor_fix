# alor_fix
Скрипт для исправления swagger файла брокера alor с прицелом на автоматическую генерацию клинта API


## Что меняет скрипт:
1. Находит заранее заданные enum и подставляет их вместо анонимных, если значения совпадают.
2. Создаёт схемы для анонимных enum.
3. Заменяет заранее известные русскоязычные теги вариантами на латиннице с сохранением изначального варианта в качестве description.
4. Ставит атрибут `required = true` для тех свойств и параметров, для которых атрибут required не прописан.
5. Добавляет `format = "int64"` для некоторых свойств, таких как, например, timestamp и id.
6. Заменяет enum со значениями "true"/"false" нормальным boolean (в теории может привести к ошибке, если сервер требует значение именно в кавычках)

## Дополнительно
  Выводит путь к свойствам с пустым или отсутствующим описанием.
