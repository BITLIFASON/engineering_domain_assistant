## Дизайн ML системы - Ассистент инженера энергетика

### 1. Цели и предпосылки
#### 1.1. Зачем создаётся решение?

- Бизнес-цель: Сократить затраты времени инженеров на проверку соответствия нормативам и составление отчёта о проверке
- Сейчас инженеры тратят большое количество времени на поиск актуальной информации в сложных неструктурированных документах, этот процесс можно ускорить с помощью ассистента

#### 1.2. Предпосылки решения

- Решение является Open Source
- Домен инженерии "Электроэнергетика"
- Наличие самостоятельного хостинга или облачных вычислений
- Коммерческий заказчик может загружать свою документацию в систему

### 2. Методология

#### 2.1. Постановка задачи

Создание RAG системы над базой знаний

#### 2.2. Блок-схема решения

Блок-схема с ключевыми этапами решения задачи.
<image src="scheme solution detailed.png" alt="Блок-схема решения">

#### 2.3. Этапы решения задачи

*Этап 1 - подготовка данных.*

В качестве документов используются правила устройства электроустановок, строительные нормы и правила, ГОСТы, своды правил, руководящие документы, федеральные законы, технические регламенты.

Основным источником документов является система "КонсультантПлюс", в качестве дополнительных источников будут выступать отдельные сайты, хранящие документы отсутствующие в основном источнике.

Документы разбиваются а части с помощью разделителя текста RecursiveCharacterTextSplitter из библиотеки LangChain, который разбивает текст на ограниченные фрагменты по абзацам и переносам с учётом размера фрагмента.

Сформированные части документов переводятся в вектора с помощью векторизатора от OpenAI (облачно) или sentence-transformers/paraphrase-multilingual-mpnet-base-v2 из HuggingFace (локально).

Полученные вектора кладутся в векторную базу данных ChromaDB.

Результатом этапа является сформированная база обработанных документов.

*Этап 2 - построение системы.*

В качестве LLM, которая принимает контекст из базы знаний используется gpt-3.5-turbo (облачно) или saiga_mistral_7b (локально).

Результатом этапа инициализированная LLM.

*Этап 3 - тестирование.*

Формирование вопросов и эталонных ответов на них.
При тестировании проверяется соответствие ответов системы эталонным ответам.
  
### 3. Подготовка пилота
  
#### 3.1. Способ оценки пилота
  
Разделение инженеров на 2 группы. Одной из них предоставляется доступ к системе. Обеим группам выдаются схожие задачи и замеряется время их выполнения.
Для проведения теста с ожидаемым эффектом понадобится выполнение 139 задач в каждой группе.
  
#### 3.2. Что считаем успешным пилотом

Уменьшение времени выполнения задач на 30 процентов
  
#### 3.3. Подготовка пилота
  
Ограничения вычислительной сложности облачной инфраструктуры OpenAI отсутствуют, однако может возникнуть ограничение по RPS основной системы
При самостоятельном хостинге на каждый токен приходится 8.5 секунд ожидания
При использовании API OpenAI необходимо несколько секунд ожидания для получения ответа

#### 3.3. Издержки

Из расчёта 139 задач по 2500 токенов на входе LLM и 500 токенов на выходе с учётом ретривера необходимо 63.74 рубля на проведение пилота.

### 4. Внедрение
  
#### 4.1. Архитектура решения
  
- Блок схема архитектуры решения.
<image src="scheme architecture.png" alt="Блок-схема архитектуры">
  
#### 4.2. Описание инфраструктуры и масштабируемости 

- Реализация пилота на инфраструктуре OpenAI, в дальнейшем MVP будет реализован на самостоятельном хостинге
- Инфраструктура OpenAI позволяет быстро собрать решение и обеспечивает высокую скорость работы системы, однако делает невозможным использовать конфиденциальные данные

#### 4.3. Требования к работе системы
  
Задержка должна быть меньше 30 секунд для оперативной помощи пользователю
  
#### 4.4. Безопасность системы
  
Потенциальная уязвимость системы заключается в использовании неправильных / некорректных (not aligned) запросов, которые могут привести к утечке данных, поэтому каждая компонента системы должна быть наделена ограничивающими правами и находиться в закрытом контуре
  
#### 4.5. Безопасность данных

- Часть данных взятая из открытых источников не является конфиденциальной и её утечка является не дырой в безопасности
- Часть данных, которая загружается заказчиком требует ограничения к ней доступа к ней в системе с помощью отдельного закрытого контура 

#### 4.5. Тонкости интеграции
  
- Парсеры занимаются проверкой актуальности источников с помощью сопоставления хэшей файлов из хранилища, и при обнаружении разных хэшей документов срабатывает триггер, по которому документы перезаписываются как в хранилище S3, так и векторной БД
- Хранилище S3 хранит документы в их исходном виде
- Векторная база данных хранит вектора чанков
- Доступ к LLM обеспечивается с помощью API OpenAI
- Интерфейс системы представлен в виде бота в Telegram
  
#### 4.6. Риски
  
- Возможно не получится поддерживать в актуальном состоянии часть документов
- Возможно ограничение доступа к облачным вычислениям
