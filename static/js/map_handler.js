// map_handler.js - Обработчик карты для интерактивной карты интернет-покрытия

// Инициализация карты
let map;
let markers = [];
let heatLayer;
let markerCluster;

// Цвета для маркеров по провайдерам
const providerColors = {
    'kt': '#0056A4',      // Казахтелеком - синий
    'beeline': '#FFCC00', // Beeline - желтый
    'almatv': '#FF6600'   // AlmaTV - оранжевый
};

// Иконки для маркеров по скорости
const speedIcons = {
    'low': L.icon({
        iconUrl: '/static/images/marker-red.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34]
    }),
    'medium': L.icon({
        iconUrl: '/static/images/marker-orange.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34]
    }),
    'high': L.icon({
        iconUrl: '/static/images/marker-green.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34]
    })
};

// Инициализация карты при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    setupEventListeners();
    loadMapData();
});

// Инициализация карты Leaflet
function initMap() {
    // Создаем карту с центром в Астане
    map = L.map('map').setView([51.1605, 71.4704], 12);
    
    // Добавляем базовый слой OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Обработчик кнопки применения фильтров
    document.getElementById('applyFilters').addEventListener('click', function() {
        loadMapData();
    });
    
    // Обработчик кнопки сброса фильтров
    document.getElementById('resetFilters').addEventListener('click', function() {
        resetFilters();
        loadMapData();
    });
    
    // Обработчики кнопок скорости
    document.getElementById('speedLow').addEventListener('click', function() {
        document.getElementById('speedRange').value = 50;
        updateSpeedRangeValue();
        loadMapData();
    });
    
    document.getElementById('speedMedium').addEventListener('click', function() {
        document.getElementById('speedRange').value = 100;
        updateSpeedRangeValue();
        loadMapData();
    });
    
    document.getElementById('speedHigh').addEventListener('click', function() {
        document.getElementById('speedRange').value = 500;
        updateSpeedRangeValue();
        loadMapData();
    });
    
    // Обработчик изменения ползунка скорости
    document.getElementById('speedRange').addEventListener('input', function() {
        updateSpeedRangeValue();
    });
    
    // Обработчики переключения режима отображения
    document.querySelectorAll('input[name="mapType"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            loadMapData();
        });
    });
    
    // Обработчики переключения провайдера
    document.querySelectorAll('input[name="provider"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            loadMapData();
        });
    });
}

// Обновление отображения значения диапазона скорости
function updateSpeedRangeValue() {
    const speedRange = document.getElementById('speedRange');
    const speedRangeValue = document.getElementById('speedRangeValue');
    speedRangeValue.textContent = `0 - ${speedRange.value}`;
}

// Сброс всех фильтров
function resetFilters() {
    // Сброс выбора провайдера
    document.getElementById('allProviders').checked = true;
    
    // Сброс режима отображения
    document.getElementById('pointsMap').checked = true;
    
    // Сброс диапазона скорости
    document.getElementById('speedRange').value = 500;
    updateSpeedRangeValue();
}

// Загрузка данных карты с сервера
function loadMapData() {
    // Получаем выбранного провайдера
    let provider = 'all';
    document.querySelectorAll('input[name="provider"]').forEach(function(radio) {
        if (radio.checked) {
            provider = radio.value;
        }
    });
    
    // Получаем диапазон скорости
    const maxSpeed = document.getElementById('speedRange').value;
    const minSpeed = 0;
    
    // Получаем режим отображения
    let mapType = 'points';
    document.querySelectorAll('input[name="mapType"]').forEach(function(radio) {
        if (radio.checked) {
            mapType = radio.value;
        }
    });
    
    // Формируем URL для запроса
    const url = `/get_map?provider=${provider}&min_speed=${minSpeed}&max_speed=${maxSpeed}&map_type=${mapType}`;
    
    // Отправляем запрос на сервер
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Ошибка при загрузке данных карты');
            }
            return response.json();
        })
        .then(data => {
            // Обрабатываем полученные данные
            updateMap(data, mapType);
            
            // Обновляем статистику
            // loadStatistics(provider, minSpeed, maxSpeed); // Статистика обновляется отдельно
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных карты:', error);
        });
}

// Обновление карты на основе полученных данных
function updateMap(data, mapType) {
    // Очищаем текущие маркеры
    clearMap();
    
    // Если данных нет, выходим
    if (!data || data.length === 0) {
        console.log('Нет данных для отображения на карте');
        return;
    }
    
    // В зависимости от типа карты отображаем точки или тепловую карту
    if (mapType === 'points') {
        // Создаем кластер маркеров для группировки
        markerCluster = L.markerClusterGroup();
        
        // Добавляем маркеры
        data.forEach(point => {
            // Определяем иконку в зависимости от скорости
            let icon;
            if (point.speed < 50) {
                icon = speedIcons.low;
            } else if (point.speed < 100) {
                icon = speedIcons.medium;
            } else {
                icon = speedIcons.high;
            }
            
            // Создаем маркер
            const marker = L.marker([point.lat, point.lng], { icon: icon });

            // Добавьте этот код перед строкой 205
            let imageUrl = "/static/img/point-default.png"; // По умолчанию
            if (point.providers.kt ) {
                imageUrl = "/static/img/provider-kt.png";
            } else if (point.providers.beeline) {
                imageUrl = "/static/img/provider-beeline.png";
            } else if (point.providers.almatv) {
                imageUrl = "/static/img/provider-almatv.png";
            }
            
            // Создаем всплывающее окно с информацией и картинкой
            let popupContent = `
                <div class="marker-popup">
                    <img src="https://via.placeholder.com/150" alt="Placeholder Image">
                    <h5>Точка интернета</h5>
                    <p><strong>Адрес:</strong> ${point.address || 'Не указан'}</p>
                    <p><strong>Скорость:</strong> ${point.speed.toFixed(1)} Мбит/с</p>
                    <p><strong>Провайдеры:</strong></p>
                    <ul>
            `;
            
            if (point.providers.kt) {
                popupContent += `<li><span style="color: ${providerColors.kt}">■</span> Казахтелеком</li>`;
            }
            if (point.providers.beeline) {
                popupContent += `<li><span style="color: ${providerColors.beeline}">■</span> Beeline</li>`;
            }
            if (point.providers.almatv) {
                popupContent += `<li><span style="color: ${providerColors.almatv}">■</span> AlmaTV</li>`;
            }
            
            popupContent += `
                    </ul>
                </div>
            `;
            
            marker.bindPopup(popupContent);
            
            // Добавляем маркер в кластер
            markerCluster.addLayer(marker);
            
            // Сохраняем маркер в массиве для возможности очистки
            markers.push(marker);
        });
        
        // Добавляем кластер на карту
        map.addLayer(markerCluster);
        
        // Подгоняем масштаб карты под все маркеры, если их больше одного
        if (data.length > 1) {
            const bounds = markerCluster.getBounds();
            map.fitBounds(bounds);
        }
    } else if (mapType.startsWith('heatmap')) {
        // Подготавливаем данные для тепловой карты
        const heatData = data.map(point => [point.lat, point.lng, point.value]);
        
        // Создаем тепловую карту
        heatLayer = L.heatLayer(heatData, {
            radius: 25,
            blur: 15,
            maxZoom: 17,
            gradient: {0.4: 'blue', 0.6: 'lime', 0.8: 'yellow', 1: 'red'}
        }).addTo(map);
    }
}

// Очистка карты от маркеров и тепловых слоев
function clearMap() {
    // Удаляем кластер маркеров
    if (markerCluster) {
        map.removeLayer(markerCluster);
    }
    
    // Удаляем отдельные маркеры
    markers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    markers = [];
    
    // Удаляем тепловой слой
    if (heatLayer && map.hasLayer(heatLayer)) {
        map.removeLayer(heatLayer);
    }
}

// Загрузка статистики
function loadStatistics(provider, minSpeed, maxSpeed) {
    const url = `/get_stats?provider=${provider}&min_speed=${minSpeed}&max_speed=${maxSpeed}`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Ошибка при загрузке статистики');
            }
            return response.json();
        })
        .then(stats => {
            // Обновляем статистику на странице
            updateStatistics(stats);
        })
        .catch(error => {
            console.error('Ошибка при загрузке статистики:', error);
        });
}

// Обновление статистики на странице
function updateStatistics(stats) {
    // Обновляем общее количество точек
    const totalPointsElement = document.getElementById('totalPoints');
    if (totalPointsElement) {
        totalPointsElement.textContent = stats.total_points;
    }
    
    // Обновляем статистику по провайдерам
    updateProviderStats('kt', stats.providers.kt);
    updateProviderStats('beeline', stats.providers.beeline);
    updateProviderStats('almatv', stats.providers.almatv);
}

// Обновление статистики по конкретному провайдеру
function updateProviderStats(provider, stats) {
    const countElement = document.getElementById(`${provider}Count`);
    const speedElement = document.getElementById(`${provider}Speed`);
    
    if (countElement) {
        countElement.textContent = stats.count;
    }
    
    if (speedElement) {
        speedElement.textContent = stats.avg_download.toFixed(1);
    }
}

// Переключение языка интерфейса
function switchLanguage(lang) {
    // Скрываем все элементы текущего языка
    document.querySelectorAll('.lang-ru, .lang-kk').forEach(el => {
        el.classList.add('d-none');
    });
    
    // Показываем элементы выбранного языка
    document.querySelectorAll(`.lang-${lang}`).forEach(el => {
        el.classList.remove('d-none');
    });
    
    // Сохраняем выбор языка в localStorage
    localStorage.setItem('preferredLanguage', lang);
}

// Установка языка при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем сохраненный язык
    const savedLang = localStorage.getItem('preferredLanguage') || 'ru';
    switchLanguage(savedLang);
    
    // Устанавливаем обработчики для кнопок переключения языка
    document.getElementById('langRu').addEventListener('click', function() {
        switchLanguage('ru');
    });
    
    document.getElementById('langKk').addEventListener('click', function() {
        switchLanguage('kk');
    });
});

