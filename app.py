from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
import json
import plotly.express as px
import plotly.graph_objects as go
import os

app = Flask(__name__)

# Загрузка данных
def load_data():
    try:
        # Путь к файлу данных
        data_file = os.path.join(os.path.dirname(__file__), '..', 'upload', 'cbm_st_pro_1.xlsx')
        
        # Загрузка данных из Excel
        df = pd.read_excel(data_file)
        
        # Вывод информации о загруженных данных
        print(f"Данные загружены успешно. Количество строк: {len(df)}")
        
        return df
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return pd.DataFrame()

# Глобальная переменная для хранения данных
df = load_data()

# Создание базовой карты
def create_base_map(center=[51.1694, 71.4491], zoom=12):
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='OpenStreetMap',
        control_scale=True
    )
    return m

# Функция для добавления точек на карту
def add_points_to_map(m, data, provider='all', min_speed=0, max_speed=500):
    # Проверка данных
    if data.empty:
        return m
    
    # Фильтрация данных
    filtered_data = data.copy()
    filtered_data = filtered_data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    
    # Фильтрация по скорости
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
    
    # Фильтрация по диапазону скорости
    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & (filtered_data[speed_column] <= max_speed)]
    
    # Выводим информацию о количестве точек для отладки
    print(f"Количество точек для отображения: {len(filtered_data)}")
    if not filtered_data.empty:
        print(f"Пример координат: {filtered_data[['latitude_speedtest', 'longitude_speedtest']].head(3).values}")
    
    # Создаем группы для каждого провайдера
    kt_group = folium.FeatureGroup(name='Казахтелеком', show=True)
    beeline_group = folium.FeatureGroup(name='Beeline', show=True)
    almatv_group = folium.FeatureGroup(name='AlmaTV', show=True)
    
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
            folium.CircleMarker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(kt_group)
        
        if row['beeline_speedtest'] == 1:
            folium.CircleMarker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(beeline_group)
        
        if row['almatv_speedtest'] == 1:
            folium.CircleMarker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(almatv_group)
    
    # Добавляем группы на карту и делаем их видимыми по умолчанию
    kt_group.add_to(m)
    beeline_group.add_to(m)
    almatv_group.add_to(m)
    
    # Отладочная информация о количестве маркеров
    print(f"Добавлено маркеров Казахтелеком: {len(filtered_data[filtered_data['kt_speedtest'] == 1])}")
    print(f"Добавлено маркеров Beeline: {len(filtered_data[filtered_data['beeline_speedtest'] == 1])}")
    print(f"Добавлено маркеров AlmaTV: {len(filtered_data[filtered_data['almatv_speedtest'] == 1])}")
    
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
    
    # Фильтрация по диапазону скорости
    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & (filtered_data[speed_column] <= max_speed)]
    
    # Подготовка данных для тепловой карты
    if heatmap_type == 'speed':
        # Тепловая карта по скорости
        heat_data = [[row['latitude_speedtest'], row['longitude_speedtest'], row[speed_column]] for _, row in filtered_data.iterrows()]
        # Создаем группу для тепловой карты
        heat_group = folium.FeatureGroup(name='Тепловая карта по скорости', show=True)
        # Добавляем тепловую карту
        HeatMap(heat_data, radius=15, max_zoom=13, gradient={0.4: 'blue', 0.65: 'lime', 0.8: 'yellow', 1: 'red'}).add_to(heat_group)
    else:
        # Тепловая карта по плотности
        heat_data = [[row['latitude_speedtest'], row['longitude_speedtest'], 1] for _, row in filtered_data.iterrows()]
        # Создаем группу для тепловой карты
        heat_group = folium.FeatureGroup(name='Тепловая карта по плотности', show=True)
        # Добавляем тепловую карту
        HeatMap(heat_data, radius=15, max_zoom=13).add_to(heat_group)
    
    # Добавляем группу на карту
    heat_group.add_to(m)
    
    return m

# Функция для получения статистики
def get_statistics(data):
    if data.empty:
        return {
            'total_points': 0,
            'providers': {
                'kt': {'count': 0, 'avg_download': 0},
                'beeline': {'count': 0, 'avg_download': 0},
                'almatv': {'count': 0, 'avg_download': 0}
            }
        }
    
    # Общее количество точек
    total_points = len(data)
    
    # Статистика по провайдерам
    kt_data = data[data['kt_speedtest'] == 1]
    beeline_data = data[data['beeline_speedtest'] == 1]
    almatv_data = data[data['almatv_speedtest'] == 1]
    
    # Средняя скорость загрузки
    kt_avg_download = kt_data['kt_download_speed'].mean() if not kt_data.empty else 0
    beeline_avg_download = beeline_data['beeline_download_speed'].mean() if not beeline_data.empty else 0
    almatv_avg_download = almatv_data['almatv_download_speed'].mean() if not almatv_data.empty else 0
    
    # Формируем статистику
    stats = {
        'total_points': total_points,
        'providers': {
            'kt': {
                'count': len(kt_data),
                'avg_download': kt_avg_download
            },
            'beeline': {
                'count': len(beeline_data),
                'avg_download': beeline_avg_download
            },
            'almatv': {
                'count': len(almatv_data),
                'avg_download': almatv_avg_download
            }
        }
    }
    
    return stats

# Функция для создания графиков
def create_charts(data, stats):
    if data.empty:
        return {}
    
    # Сравнение средних скоростей провайдеров
    providers_comparison = go.Figure(data=[
        go.Bar(
            x=['Казахтелеком', 'Beeline', 'AlmaTV'],
            y=[stats['providers']['kt']['avg_download'], 
               stats['providers']['beeline']['avg_download'], 
               stats['providers']['almatv']['avg_download']],
            marker_color=['#0056A4', '#FFCC00', '#FF6600']
        )
    ])
    providers_comparison.update_layout(
        title='Сравнение средних скоростей провайдеров',
        xaxis_title='Провайдер',
        yaxis_title='Средняя скорость загрузки (Мбит/с)',
        template='plotly_white'
    )
    
    # Доля провайдеров по количеству точек
    providers_pie = go.Figure(data=[
        go.Pie(
            labels=['Казахтелеком', 'Beeline', 'AlmaTV'],
            values=[stats['providers']['kt']['count'], 
                   stats['providers']['beeline']['count'], 
                   stats['providers']['almatv']['count']],
            marker_colors=['#0056A4', '#FFCC00', '#FF6600']
        )
    ])
    providers_pie.update_layout(
        title='Доля провайдеров по количеству точек',
        template='plotly_white'
    )
    
    # Гистограммы распределения скорости для каждого провайдера
    kt_data = data[data['kt_speedtest'] == 1]
    beeline_data = data[data['beeline_speedtest'] == 1]
    almatv_data = data[data['almatv_speedtest'] == 1]
    
    kt_hist = go.Figure()
    if not kt_data.empty:
        kt_hist.add_trace(go.Histogram(
            x=kt_data['kt_download_speed'],
            marker_color='#0056A4',
            nbinsx=20
        ))
    kt_hist.update_layout(
        title='Распределение скорости Казахтелеком',
        xaxis_title='Скорость загрузки (Мбит/с)',
        yaxis_title='Количество точек',
        template='plotly_white'
    )
    
    beeline_hist = go.Figure()
    if not beeline_data.empty:
        beeline_hist.add_trace(go.Histogram(
            x=beeline_data['beeline_download_speed'],
            marker_color='#FFCC00',
            nbinsx=20
        ))
    beeline_hist.update_layout(
        title='Распределение скорости Beeline',
        xaxis_title='Скорость загрузки (Мбит/с)',
        yaxis_title='Количество точек',
        template='plotly_white'
    )
    
    almatv_hist = go.Figure()
    if not almatv_data.empty:
        almatv_hist.add_trace(go.Histogram(
            x=almatv_data['almatv_download_speed'],
            marker_color='#FF6600',
            nbinsx=20
        ))
    almatv_hist.update_layout(
        title='Распределение скорости AlmaTV',
        xaxis_title='Скорость загрузки (Мбит/с)',
        yaxis_title='Количество точек',
        template='plotly_white'
    )
    
    # Топ-10 городов по количеству точек
    if 'city' in data.columns:
        city_counts = data['city'].value_counts().head(10)
        cities_bar = go.Figure(data=[
            go.Bar(
                x=city_counts.index,
                y=city_counts.values,
                marker_color='#0056A4'
            )
        ])
        cities_bar.update_layout(
            title='Топ-10 городов по количеству точек',
            xaxis_title='Город',
            yaxis_title='Количество точек',
            template='plotly_white'
        )
    else:
        cities_bar = go.Figure()
        cities_bar.update_layout(
            title='Данные о городах отсутствуют',
            template='plotly_white'
        )
    
    # Формируем словарь с графиками
    charts = {
        'providers_comparison': json.dumps(providers_comparison, cls=plotly.utils.PlotlyJSONEncoder),
        'providers_pie': json.dumps(providers_pie, cls=plotly.utils.PlotlyJSONEncoder),
        'kt_hist': json.dumps(kt_hist, cls=plotly.utils.PlotlyJSONEncoder),
        'beeline_hist': json.dumps(beeline_hist, cls=plotly.utils.PlotlyJSONEncoder),
        'almatv_hist': json.dumps(almatv_hist, cls=plotly.utils.PlotlyJSONEncoder),
        'cities_bar': json.dumps(cities_bar, cls=plotly.utils.PlotlyJSONEncoder)
    }
    
    return charts

# Маршруты Flask
@app.route('/')
def index():
    # Проверяем данные
    if df.empty:
        return render_template('error.html', message="Ошибка загрузки данных. Проверьте файл данных.")
    
    # Получаем параметры из запроса
    map_type = request.args.get('map_type', 'points')
    provider = request.args.get('provider', 'all')
    min_speed = int(request.args.get('min_speed', 0))
    max_speed = int(request.args.get('max_speed', 500))
    lang = request.args.get('lang', 'ru')
    
    # Создаем базовую карту
    m = create_base_map()
    
    # Добавляем слои на карту в зависимости от выбранного типа
    if map_type == 'points':
        m = add_points_to_map(m, df, provider, min_speed, max_speed)
    elif map_type == 'heatmap_speed':
        m = add_heatmap_to_map(m, df, provider, min_speed, max_speed, 'speed')
    elif map_type == 'heatmap_density':
        m = add_heatmap_to_map(m, df, provider, min_speed, max_speed, 'density')
    
    # Добавляем контроль слоев
    folium.LayerControl().add_to(m)
    
    # Получаем статистику
    stats = get_statistics(df)
    
    # Создаем графики
    charts = create_charts(df, stats)
    
    # Сохраняем карту во временный файл
    map_html = m._repr_html_()
    
    return render_template('index.html', 
                          map_html=map_html,
                          stats=stats,
                          charts=charts,
                          lang=lang)

@app.route('/analytics')
def analytics():
    # Проверяем данные
    if df.empty:
        return render_template('error.html', message="Ошибка загрузки данных. Проверьте файл данных.")
    
    # Получаем параметры из запроса
    provider = request.args.get('provider', 'all')
    min_speed = int(request.args.get('min_speed', 0))
    max_speed = int(request.args.get('max_speed', 500))
    lang = request.args.get('lang', 'ru')
    
    # Получаем статистику
    stats = get_statistics(df)
    
    # Создаем графики
    charts = create_charts(df, stats)
    
    return render_template('analytics.html', 
                          stats=stats,
                          charts=charts,
                          lang=lang)

@app.route('/update_map')
def update_map():
    # Получаем параметры из запроса
    map_type = request.args.get('map_type', 'points')
    provider = request.args.get('provider', 'all')
    min_speed = int(request.args.get('min_speed', 0))
    max_speed = int(request.args.get('max_speed', 500))
    
    # Создаем базовую карту
    m = create_base_map()
    
    # Добавляем слои на карту в зависимости от выбранного типа
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

@app.route('/get_stats')
def get_stats():
    # Получаем параметры из запроса
    provider = request.args.get('provider', 'all')
    min_speed = int(request.args.get('min_speed', 0))
    max_speed = int(request.args.get('max_speed', 500))
    
    # Фильтруем данные
    filtered_data = df.copy()
    
    # Фильтрация по провайдеру
    if provider != 'all':
        if provider == 'kt':
            filtered_data = filtered_data[filtered_data['kt_speedtest'] == 1]
        elif provider == 'beeline':
            filtered_data = filtered_data[filtered_data['beeline_speedtest'] == 1]
        elif provider == 'almatv':
            filtered_data = filtered_data[filtered_data['almatv_speedtest'] == 1]
    
    # Фильтрация по скорости
    if provider == 'kt':
        filtered_data = filtered_data[(filtered_data['kt_download_speed'] >= min_speed) & (filtered_data['kt_download_speed'] <= max_speed)]
    elif provider == 'beeline':
        filtered_data = filtered_data[(filtered_data['beeline_download_speed'] >= min_speed) & (filtered_data['beeline_download_speed'] <= max_speed)]
    elif provider == 'almatv':
        filtered_data = filtered_data[(filtered_data['almatv_download_speed'] >= min_speed) & (filtered_data['almatv_download_speed'] <= max_speed)]
    else:
        # Для всех провайдеров используем максимальную скорость из доступных
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        filtered_data = filtered_data[(filtered_data['max_download_speed'] >= min_speed) & (filtered_data['max_download_speed'] <= max_speed)]
    
    # Получаем статистику
    stats = get_statistics(filtered_data)
    
    return jsonify(stats)

@app.route('/get_charts')
def get_charts():
    # Получаем параметры из запроса
    provider = request.args.get('provider', 'all')
    min_speed = int(request.args.get('min_speed', 0))
    max_speed = int(request.args.get('max_speed', 500))
    
    # Фильтруем данные
    filtered_data = df.copy()
    
    # Фильтрация по провайдеру
    if provider != 'all':
        if provider == 'kt':
            filtered_data = filtered_data[filtered_data['kt_speedtest'] == 1]
        elif provider == 'beeline':
            filtered_data = filtered_data[filtered_data['beeline_speedtest'] == 1]
        elif provider == 'almatv':
            filtered_data = filtered_data[filtered_data['almatv_speedtest'] == 1]
    
    # Фильтрация по скорости
    if provider == 'kt':
        filtered_data = filtered_data[(filtered_data['kt_download_speed'] >= min_speed) & (filtered_data['kt_download_speed'] <= max_speed)]
    elif provider == 'beeline':
        filtered_data = filtered_data[(filtered_data['beeline_download_speed'] >= min_speed) & (filtered_data['beeline_download_speed'] <= max_speed)]
    elif provider == 'almatv':
        filtered_data = filtered_data[(filtered_data['almatv_download_speed'] >= min_speed) & (filtered_data['almatv_download_speed'] <= max_speed)]
    else:
        # Для всех провайдеров используем максимальную скорость из доступных
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        filtered_data = filtered_data[(filtered_data['max_download_speed'] >= min_speed) & (filtered_data['max_download_speed'] <= max_speed)]
    
    # Получаем статистику
    stats = get_statistics(filtered_data)
    
    # Создаем графики
    charts = create_charts(filtered_data, stats)
    
    return jsonify(charts)

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

