from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
import plotly.express as px
import plotly.graph_objects as go
import json
import os

app = Flask(__name__)

# Загрузка данных
try:
    df = pd.read_excel('data/cbm_st_pro_1.xlsx')
    print(f"Данные загружены успешно. Количество строк: {len(df)}")
except Exception as e:
    print(f"Ошибка при загрузке данных: {e}")
    df = pd.DataFrame()  # Пустой DataFrame в случае ошибки

# Функция для создания базовой карты
def create_base_map():
    # Центрируем карту на Астане
    m = folium.Map(location=[51.1605, 71.4704], zoom_start=12, tiles='CartoDB positron')
    return m

# Функция для проверки и очистки данных
def validate_data(data):
    if data.empty:
        print("Ошибка: данные пусты")
        return False
    
    # Проверяем наличие необходимых колонок
    required_columns = ['latitude_speedtest', 'longitude_speedtest', 
                        'kt_speedtest', 'beeline_speedtest', 'almatv_speedtest',
                        'kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']
    
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        print(f"Ошибка: отсутствуют колонки {missing_columns}")
        return False
    
    # Проверяем валидность координат
    valid_data = data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    valid_data = valid_data[(valid_data['latitude_speedtest'] >= -90) & (valid_data['latitude_speedtest'] <= 90)]
    valid_data = valid_data[(valid_data['longitude_speedtest'] >= -180) & (valid_data['longitude_speedtest'] <= 180)]
    
    # Проверяем наличие данных после фильтрации
    if len(valid_data) == 0:
        print("Ошибка: нет валидных данных после проверки")
        return False
    
    print(f"Данные прошли валидацию. Валидных строк: {len(valid_data)}")
    return True

# Функция для добавления точек на карту
def add_points_to_map(m, data, provider='all', min_speed=0, max_speed=500):
    # Проверка данных перед обработкой
    if data.empty:
        folium.Marker(
            location=[51.1605, 71.4704],
            popup="Ошибка загрузки данных. Пожалуйста, проверьте формат данных.",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)
        return m
    
    # Фильтрация данных
    filtered_data = data.copy()
    
    # Удаляем строки с отсутствующими координатами
    filtered_data = filtered_data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    
    # Определяем колонку скорости в зависимости от провайдера
    if provider != 'all':
        if provider == 'kt':
            filtered_data = filtered_data[filtered_data['kt_speedtest'] == 1]
            speed_column = 'kt_download_speed'
        elif provider == 'beeline':
            filtered_data = filtered_data[filtered_data['beeline_speedtest'] == 1]
            speed_column = 'beeline_download_speed'
        elif provider == 'almatv':
            filtered_data = filtered_data[filtered_data['almatv_speedtest'] == 1]
            speed_column = 'almatv_download_speed'
    else:
        # Для всех провайдеров используем максимальную скорость из доступных
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'
    
    # Фильтрация по скорости
    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & 
                                 (filtered_data[speed_column] <= max_speed)]
    
    # Проверяем, остались ли данные после фильтрации
    if len(filtered_data) == 0:
        folium.Marker(
            location=[51.1605, 71.4704],
            popup="Нет данных, соответствующих выбранным фильтрам",
            icon=folium.Icon(color="orange", icon="info-sign")
        ).add_to(m)
        return m
    
    # Выводим информацию о количестве точек для отладки
    print(f"Количество точек для отображения: {len(filtered_data)}")
    print(f"Пример координат: {filtered_data[['latitude_speedtest', 'longitude_speedtest']].head(3).values}")
    
    # Создаем группы для каждого провайдера
    kt_group = folium.FeatureGroup(name='Казахтелеком')
    beeline_group = folium.FeatureGroup(name='Beeline')
    almatv_group = folium.FeatureGroup(name='AlmaTV')
    
    # Добавляем точки на карту
    for _, row in filtered_data.iterrows():
        # Определяем скорость для текущей точки
        if provider != 'all':
            current_speed = row[speed_column]
        else:
            current_speed = row['max_download_speed']
            
        # Определяем цвет маркера в зависимости от скорости
        if current_speed < 50:
            color = 'red'
        elif current_speed < 100:
            color = 'orange'
        else:
            color = 'green'
        
        # Создаем всплывающее окно
        popup_html = f"""
        <div style="width: 250px; padding: 10px; font-family: Arial, sans-serif;">
            <h4 style="margin-top: 0; color: #0056A4; font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 5px;">{row['address'] if 'address' in row else 'Точка интернета'}</h4>
            <p style="margin: 8px 0;"><b>Скорость загрузки:</b> {current_speed:.1f} Мбит/с</p>
            <p style="margin: 8px 0; background-color: #f8f9fa; padding: 5px; border-radius: 4px;"><b>Координаты:</b> {row['latitude_speedtest']:.6f}, {row['longitude_speedtest']:.6f}</p>
            <p style="margin: 8px 0;"><b>Провайдеры:</b></p>
            <ul style="margin: 5px 0; padding-left: 20px;">
                {'<li style="color: #0056A4;">Казахтелеком</li>' if row['kt_speedtest'] == 1 else ''}
                {'<li style="color: #FFCC00;">Beeline</li>' if row['beeline_speedtest'] == 1 else ''}
                {'<li style="color: #FF6600;">AlmaTV</li>' if row['almatv_speedtest'] == 1 else ''}
            </ul>
        </div>
        """
        
        # Создаем попап с фиксированной шириной
        popup = folium.Popup(popup_html, max_width=300)
        
        # Добавляем маркер в соответствующую группу
        if row['kt_speedtest'] == 1:
            folium.Marker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                icon=folium.Icon(color=color, icon='wifi', prefix='fa')
            ).add_to(kt_group)
        
        if row['beeline_speedtest'] == 1:
            folium.Marker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                icon=folium.Icon(color=color, icon='wifi', prefix='fa')
            ).add_to(beeline_group)
        
        if row['almatv_speedtest'] == 1:
            folium.Marker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                icon=folium.Icon(color=color, icon='wifi', prefix='fa')
            ).add_to(almatv_group)
    
    # Добавляем группы на карту
    kt_group.add_to(m)
    beeline_group.add_to(m)
    almatv_group.add_to(m)
    
    return m

# Функция для добавления тепловой карты
def add_heatmap_to_map(m, data, provider='all', min_speed=0, max_speed=500, heatmap_type='speed'):
    # Проверка данных
    if data.empty:
        return m
    
    # Фильтрация данных
    filtered_data = data.copy()
    filtered_data = filtered_data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    
    # Определяем колонку скорости в зависимости от провайдера
    if provider != 'all':
        if provider == 'kt':
            filtered_data = filtered_data[filtered_data['kt_speedtest'] == 1]
            speed_column = 'kt_download_speed'
        elif provider == 'beeline':
            filtered_data = filtered_data[filtered_data['beeline_speedtest'] == 1]
            speed_column = 'beeline_download_speed'
        elif provider == 'almatv':
            filtered_data = filtered_data[filtered_data['almatv_speedtest'] == 1]
            speed_column = 'almatv_download_speed'
    else:
        # Для всех провайдеров используем максимальную скорость из доступных
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'
    
    # Фильтрация по скорости
    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & 
                                 (filtered_data[speed_column] <= max_speed)]
    
    # Подготовка данных для тепловой карты
    if heatmap_type == 'speed':
        # Тепловая карта по скорости
        heat_data = [[row['latitude_speedtest'], row['longitude_speedtest'], row[speed_column]] 
                     for _, row in filtered_data.iterrows()]
        name = 'Тепловая карта скорости'
    else:
        # Тепловая карта по плотности
        heat_data = [[row['latitude_speedtest'], row['longitude_speedtest'], 1] 
                     for _, row in filtered_data.iterrows()]
        name = 'Тепловая карта плотности'
    
    # Добавляем тепловую карту
    if heat_data:
        HeatMap(heat_data, name=name, min_opacity=0.3, radius=15).add_to(m)
    
    return m

# Функция для получения статистики
def get_statistics(data):
    if data.empty:
        return {
            'total_points': 0,
            'providers': {
                'kt': {'count': 0, 'avg_download': 0, 'avg_upload': 0},
                'beeline': {'count': 0, 'avg_download': 0, 'avg_upload': 0},
                'almatv': {'count': 0, 'avg_download': 0, 'avg_upload': 0}
            }
        }
    
    # Очищаем данные от NaN в координатах
    data = data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    
    stats = {
        'total_points': len(data),
        'providers': {
            'kt': {
                'count': int(data['kt_speedtest'].sum()),
                'avg_download': float(data[data['kt_speedtest'] == 1]['kt_download_speed'].mean()) if data[data['kt_speedtest'] == 1].shape[0] > 0 else 0,
                'avg_upload': float(data[data['kt_speedtest'] == 1]['kt_upload_speed'].mean()) if data[data['kt_speedtest'] == 1].shape[0] > 0 else 0
            },
            'beeline': {
                'count': int(data['beeline_speedtest'].sum()),
                'avg_download': float(data[data['beeline_speedtest'] == 1]['beeline_download_speed'].mean()) if data[data['beeline_speedtest'] == 1].shape[0] > 0 else 0,
                'avg_upload': float(data[data['beeline_speedtest'] == 1]['beeline_upload_speed'].mean()) if data[data['beeline_speedtest'] == 1].shape[0] > 0 else 0
            },
            'almatv': {
                'count': int(data['almatv_speedtest'].sum()),
                'avg_download': float(data[data['almatv_speedtest'] == 1]['almatv_download_speed'].mean()) if data[data['almatv_speedtest'] == 1].shape[0] > 0 else 0,
                'avg_upload': float(data[data['almatv_speedtest'] == 1]['almatv_upload_speed'].mean()) if data[data['almatv_speedtest'] == 1].shape[0] > 0 else 0
            }
        }
    }
    
    # Добавляем статистику по городам, если есть колонка isb_town
    if 'isb_town' in data.columns:
        stats['cities'] = data.groupby('isb_town').size().to_dict()
    else:
        stats['cities'] = {}
    
    return stats

# Функция для создания графиков
def create_charts(data, stats):
    if data.empty:
        # Создаем пустые графики с сообщением об отсутствии данных
        empty_message = "Нет данных для отображения"
        
        kt_hist = px.histogram(title='Распределение скорости Казахтелеком')
        kt_hist.update_layout(annotations=[dict(text=empty_message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        beeline_hist = px.histogram(title='Распределение скорости Beeline')
        beeline_hist.update_layout(annotations=[dict(text=empty_message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        almatv_hist = px.histogram(title='Распределение скорости AlmaTV')
        almatv_hist.update_layout(annotations=[dict(text=empty_message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        providers_comparison = go.Figure()
        providers_comparison.update_layout(title='Сравнение средних скоростей провайдеров',
                                          annotations=[dict(text=empty_message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        providers_pie = go.Figure()
        providers_pie.update_layout(title='Доля провайдеров по количеству точек',
                                   annotations=[dict(text=empty_message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        cities_bar = px.bar(title='Топ-10 городов по количеству точек')
        cities_bar.update_layout(annotations=[dict(text=empty_message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
    else:
        # Очищаем данные от NaN в координатах
        data = data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
        
        # 1. Гистограммы распределения скорости для каждого провайдера
        kt_data = data[data['kt_speedtest'] == 1]
        beeline_data = data[data['beeline_speedtest'] == 1]
        almatv_data = data[data['almatv_speedtest'] == 1]
        
        if len(kt_data) > 0:
            kt_hist = px.histogram(kt_data, x='kt_download_speed', nbins=20, 
                                  title='Распределение скорости Казахтелеком',
                                  labels={'kt_download_speed': 'Скорость (Мбит/с)', 'count': 'Количество точек'},
                                  color_discrete_sequence=['#0056A4'])
        else:
            kt_hist = px.histogram(title='Распределение скорости Казахтелеком')
            kt_hist.update_layout(annotations=[dict(text="Нет данных для Казахтелеком", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        if len(beeline_data) > 0:
            beeline_hist = px.histogram(beeline_data, x='beeline_download_speed', nbins=20,
                                       title='Распределение скорости Beeline',
                                       labels={'beeline_download_speed': 'Скорость (Мбит/с)', 'count': 'Количество точек'},
                                       color_discrete_sequence=['#FFCC00'])
        else:
            beeline_hist = px.histogram(title='Распределение скорости Beeline')
            beeline_hist.update_layout(annotations=[dict(text="Нет данных для Beeline", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        if len(almatv_data) > 0:
            almatv_hist = px.histogram(almatv_data, x='almatv_download_speed', nbins=20,
                                      title='Распределение скорости AlmaTV',
                                      labels={'almatv_download_speed': 'Скорость (Мбит/с)', 'count': 'Количество точек'},
                                      color_discrete_sequence=['#FF6600'])
        else:
            almatv_hist = px.histogram(title='Распределение скорости AlmaTV')
            almatv_hist.update_layout(annotations=[dict(text="Нет данных для AlmaTV", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
        
        # 2. Сравнение средних скоростей провайдеров
        providers_comparison = go.Figure(data=[
            go.Bar(name='Скорость загрузки', 
                   x=['Казахтелеком', 'Beeline', 'AlmaTV'], 
                   y=[stats['providers']['kt']['avg_download'], 
                      stats['providers']['beeline']['avg_download'], 
                      stats['providers']['almatv']['avg_download']],
                   marker_color=['#0056A4', '#FFCC00', '#FF6600']),
            go.Bar(name='Скорость выгрузки', 
                   x=['Казахтелеком', 'Beeline', 'AlmaTV'], 
                   y=[stats['providers']['kt']['avg_upload'], 
                      stats['providers']['beeline']['avg_upload'], 
                      stats['providers']['almatv']['avg_upload']],
                   marker_color=['#4D94DB', '#FFE066', '#FF9966'])
        ])
        providers_comparison.update_layout(title='Сравнение средних скоростей провайдеров',
                                          xaxis_title='Провайдер',
                                          yaxis_title='Скорость (Мбит/с)',
                                          barmode='group')
        
        # 3. Круговая диаграмма доли провайдеров
        providers_pie = go.Figure(data=[go.Pie(
            labels=['Казахтелеком', 'Beeline', 'AlmaTV'],
            values=[stats['providers']['kt']['count'], 
                    stats['providers']['beeline']['count'], 
                    stats['providers']['almatv']['count']],
            marker_colors=['#0056A4', '#FFCC00', '#FF6600'],
            hole=.3
        )])
        providers_pie.update_layout(title='Доля провайдеров по количеству точек')
        
        # 4. Топ-10 городов по количеству точек
        if 'cities' in stats and stats['cities']:
            cities_data = pd.DataFrame(list(stats['cities'].items()), columns=['city', 'count'])
            cities_data = cities_data.sort_values('count', ascending=False).head(10)
            
            cities_bar = px.bar(cities_data, x='city', y='count',
                               title='Топ-10 городов по количеству точек',
                               labels={'city': 'Город', 'count': 'Количество точек'},
                               color_discrete_sequence=['#0056A4'])
        else:
            cities_bar = px.bar(title='Топ-10 городов по количеству точек')
            cities_bar.update_layout(annotations=[dict(text="Нет данных о городах", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)])
    
    # Преобразуем графики в JSON для передачи в шаблон
    charts = {
        'kt_hist': kt_hist.to_json(),
        'beeline_hist': beeline_hist.to_json(),
        'almatv_hist': almatv_hist.to_json(),
        'providers_comparison': providers_comparison.to_json(),
        'providers_pie': providers_pie.to_json(),
        'cities_bar': cities_bar.to_json()
    }
    
    return charts

# Главная страница с картой
@app.route('/')
def index():
    # Проверяем данные
    if df.empty:
        return render_template('error.html', message="Ошибка загрузки данных. Проверьте файл данных.")
    
    # Создаем базовую карту
    m = create_base_map()
    
    # Добавляем точки на карту
    m = add_points_to_map(m, df)
    
    # Добавляем контроль слоев
    folium.LayerControl().add_to(m)
    
    # Получаем статистику
    stats = get_statistics(df)
    
    # Сохраняем карту во временный файл
    map_html = m._repr_html_()
    
    return render_template('index.html', 
                          map_html=map_html,
                          stats=stats)

# Страница аналитики
@app.route('/analytics')
def analytics():
    # Проверяем данные
    if df.empty:
        return render_template('error.html', message="Ошибка загрузки данных. Проверьте файл данных.")
    
    # Получаем статистику
    stats = get_statistics(df)
    
    # Создаем графики
    charts = create_charts(df, stats)
    
    return render_template('analytics.html', 
                          stats=stats,
                          charts=charts)

# API для обновления карты при изменении фильтров
@app.route('/update_map', methods=['GET'])
def update_map():
    # Получаем параметры фильтрации
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))
    map_type = request.args.get('map_type', 'points')
    
    # Создаем базовую карту
    m = create_base_map()
    
    # Добавляем соответствующий слой в зависимости от типа карты
    if map_type == 'points':
        m = add_points_to_map(m, df, provider, min_speed, max_speed)
    elif map_type == 'heatmap_speed':
        m = add_heatmap_to_map(m, df, provider, min_speed, max_speed, 'speed')
    elif map_type == 'heatmap_density':
        m = add_heatmap_to_map(m, df, provider, min_speed, max_speed, 'density')
    
    # Добавляем контроль слоев
    folium.LayerControl().add_to(m)
    
    # Возвращаем HTML-код карты
    return m._repr_html_()

# Маршрут для получения статистики
@app.route('/get_stats')
def get_stats():
    # Получаем параметры фильтрации
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))
    
    # Фильтруем данные
    filtered_data = df.copy()
    
    if provider != 'all':
        if provider == 'kt':
            filtered_data = filtered_data[filtered_data['kt_speedtest'] == 1]
        elif provider == 'beeline':
            filtered_data = filtered_data[filtered_data['beeline_speedtest'] == 1]
        elif provider == 'almatv':
            filtered_data = filtered_data[filtered_data['almatv_speedtest'] == 1]
    
    # Получаем статистику
    stats = get_statistics(filtered_data)
    
    return jsonify(stats)

# Маршрут для получения графиков
@app.route('/get_charts')
def get_charts():
    # Получаем параметры фильтрации
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))
    
    # Фильтруем данные
    filtered_data = df.copy()
    
    if provider != 'all':
        if provider == 'kt':
            filtered_data = filtered_data[filtered_data['kt_speedtest'] == 1]
        elif provider == 'beeline':
            filtered_data = filtered_data[filtered_data['beeline_speedtest'] == 1]
        elif provider == 'almatv':
            filtered_data = filtered_data[filtered_data['almatv_speedtest'] == 1]
    
    # Получаем статистику
    stats = get_statistics(filtered_data)
    
    # Создаем графики
    charts = create_charts(filtered_data, stats)
    
    return jsonify(charts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
