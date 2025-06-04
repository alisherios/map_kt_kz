// Функция для переключения языка
function switchLanguage(lang) {
    console.log('Переключение языка на: ' + lang);
    
    // Скрываем все языковые элементы
    document.querySelectorAll('.lang-ru, .lang-kk').forEach(el => {
        el.classList.add('d-none');
    });
    
    // Показываем элементы выбранного языка
    document.querySelectorAll('.lang-' + lang).forEach(el => {
        el.classList.remove('d-none');
    });
    
    // Обновляем активную кнопку
    document.querySelectorAll('.language-switcher .btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Находим и активируем кнопку выбранного языка
    const langButton = document.querySelector('.language-switcher .btn[data-lang="' + lang + '"]');
    if (langButton) {
        langButton.classList.add('active');
    } else {
        console.error('Кнопка языка не найдена: ' + lang);
    }
    
    // Сохраняем выбор в localStorage
    localStorage.setItem('preferred_language', lang);
    
    // Обновляем атрибут lang у html элемента
    document.documentElement.lang = lang;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен, инициализация переключателя языка');
    
    // Получаем сохраненный язык или используем русский по умолчанию
    const savedLang = localStorage.getItem('preferred_language') || 'ru';
    console.log('Сохраненный язык: ' + savedLang);
    
    // Небольшая задержка для гарантии полной загрузки DOM
    setTimeout(() => {
        switchLanguage(savedLang);
        
        // Добавляем обработчики событий для кнопок переключения языка
        document.querySelectorAll('.language-switcher .btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const lang = this.getAttribute('data-lang');
                console.log('Клик по кнопке языка: ' + lang);
                switchLanguage(lang);
            });
        });
    }, 100);
});
