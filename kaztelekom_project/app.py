from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
import plotly.express as px
import plotly.graph_objects as go

app = Flask(__name__)

# Загрузка данных
df = pd.read_excel('data/cbm_st_pro_1.xlsx')

# Функция для создания базовой карты
def create_base_map():
    m = folium.Map(location=[48.0196, 66.9237], zoom_start=5, tiles='CartoDB positron')
    return m

# Функция для добавления точек на карту
def add_points_to_map(m, data, provider='all', min_speed=0, max_speed=500):
    # Фильтрация данных
    filtered_data = data.copy()
    
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
        <div style="width: 200px;">
            <h4>{row['address']}</h4>
            <p><b>Скорость загрузки:</b> {current_speed:.1f} Мбит/с</p>
            <p><b>Провайдеры:</b></p>
            <ul>
                {'<li>Казахтелеком</li>' if row['kt_speedtest'] == 1 else ''}
                {'<li>Beeline</li>' if row['beeline_speedtest'] == 1 else ''}
                {'<li>AlmaTV</li>' if row['almatv_speedtest'] == 1 else ''}
            </ul>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=300)
        
        # Добавляем маркер в соответствующую группу
        if row['kt_speedtest'] == 1:
            folium.CircleMarker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                radius=5,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=popup
            ).add_to(kt_group)
        
        if row['beeline_speedtest'] == 1:
            folium.CircleMarker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                radius=5,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=popup
            ).add_to(beeline_group)
        
        if row['almatv_speedtest'] == 1:
            folium.CircleMarker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                radius=5,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=popup
            ).add_to(almatv_group)
    
    # Добавляем группы на карту
    kt_group.add_to(m)
    beeline_group.add_to(m)
    almatv_group.add_to(m)
    
    return m

# Функция для добавления тепловой карты
def add_heatmap_to_map(m, data, provider='all', min_speed=0, max_speed=500, heatmap_type='speed'):
    # Фильтрация данных
    filtered_data = data.copy()
    
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
    stats = {
        'total_points': len(data),
        'providers': {
            'kt': {
                'count': int(data['kt_speedtest'].sum()),
                'avg_download': float(data[data['kt_speedtest'] == 1]['kt_download_speed'].mean()),
                'avg_upload': float(data[data['kt_speedtest'] == 1]['kt_upload_speed'].mean()),
                'avg_ping': 0  # Пинг отсутствует в данных
            },
            'beeline': {
                'count': int(data['beeline_speedtest'].sum()),
                'avg_download': float(data[data['beeline_speedtest'] == 1]['beeline_download_speed'].mean()),
                'avg_upload': float(data[data['beeline_speedtest'] == 1]['beeline_upload_speed'].mean()),
                'avg_ping': 0  # Пинг отсутствует в данных
            },
            'almatv': {
                'count': int(data['almatv_speedtest'].sum()),
                'avg_download': float(data[data['almatv_speedtest'] == 1]['almatv_download_speed'].mean()),
                'avg_upload': float(data[data['almatv_speedtest'] == 1]['almatv_upload_speed'].mean()),
                'avg_ping': 0  # Пинг отсутствует в данных
            }
        },
        'cities': data.groupby('isb_town').size().to_dict()
    }
    
    return stats

# Функция для создания графиков
def create_charts(data, stats, filtered=False):
    # 1. Гистограммы распределения скорости для каждого провайдера
    kt_data = data[data['kt_speedtest'] == 1]
    beeline_data = data[data['beeline_speedtest'] == 1]
    almatv_data = data[data['almatv_speedtest'] == 1]
    
    kt_hist = px.histogram(kt_data, x='kt_download_speed', nbins=20, 
                          title='Распределение скорости Казахтелеком',
                          labels={'kt_download_speed': 'Скорость (Мбит/с)', 'count': 'Количество точек'},
                          color_discrete_sequence=['#0056A4'])
    kt_hist.update_layout(template='plotly_white')
    
    beeline_hist = px.histogram(beeline_data, x='beeline_download_speed', nbins=20, 
                               title='Распределение скорости Beeline',
                               labels={'beeline_download_speed': 'Скорость (Мбит/с)', 'count': 'Количество точек'},
                               color_discrete_sequence=['#FFCC00'])
    beeline_hist.update_layout(template='plotly_white')
    
    almatv_hist = px.histogram(almatv_data, x='almatv_download_speed', nbins=20, 
                              title='Распределение скорости AlmaTV',
                              labels={'almatv_download_speed': 'Скорость (Мбит/с)', 'count': 'Количество точек'},
                              color_discrete_sequence=['#FF6600'])
    almatv_hist.update_layout(template='plotly_white')
    
    # 2. Сравнение средних скоростей провайдеров
    providers_comparison = go.Figure()
    providers_comparison.add_trace(go.Bar(
        x=['Казахтелеком', 'Beeline', 'AlmaTV'],
        y=[stats['providers']['kt']['avg_download'], 
           stats['providers']['beeline']['avg_download'], 
           stats['providers']['almatv']['avg_download']],
        name='Скорость загрузки',
        marker_color=['#0056A4', '#FFCC00', '#FF6600']
    ))
    providers_comparison.add_trace(go.Bar(
        x=['Казахтелеком', 'Beeline', 'AlmaTV'],
        y=[stats['providers']['kt']['avg_upload'], 
           stats['providers']['beeline']['avg_upload'], 
           stats['providers']['almatv']['avg_upload']],
        name='Скорость выгрузки',
        marker_color=['#66A3D2', '#FFE066', '#FFAA66']
    ))
    providers_comparison.update_layout(
        title='Сравнение средних скоростей провайдеров',
        xaxis_title='Провайдер',
        yaxis_title='Скорость (Мбит/с)',
        barmode='group',
        template='plotly_white'
    )
    
    # 3. Круговая диаграмма доли провайдеров
    providers_pie = go.Figure(data=[go.Pie(
        labels=['Казахтелеком', 'Beeline', 'AlmaTV'],
        values=[stats['providers']['kt']['count'], 
                stats['providers']['beeline']['count'], 
                stats['providers']['almatv']['count']],
        hole=.3,
        marker_colors=['#0056A4', '#FFCC00', '#FF6600']
    )])
    providers_pie.update_layout(
        title='Доля провайдеров по количеству точек',
        template='plotly_white'
    )
    
    # 4. Карта городов с количеством точек
    cities_data = pd.DataFrame({
        'city': list(stats['cities'].keys()),
        'count': list(stats['cities'].values())
    }).sort_values('count', ascending=False).head(10)
    
    cities_bar = px.bar(cities_data, x='city', y='count',
                       title='Топ-10 городов по количеству точек',
                       labels={'city': 'Город', 'count': 'Количество точек'},
                       color='count',
                       color_continuous_scale='Blues')
    cities_bar.update_layout(template='plotly_white')
    
    # Преобразуем графики в JSON для передачи на фронтенд
    charts = {
        'kt_hist': kt_hist.to_json(),
        'beeline_hist': beeline_hist.to_json(),
        'almatv_hist': almatv_hist.to_json(),
        'providers_comparison': providers_comparison.to_json(),
        'providers_pie': providers_pie.to_json(),
        'cities_bar': cities_bar.to_json()
    }
    
    return charts

# Маршрут для главной страницы
@app.route('/')
def index():
    # Создаем базовую карту
    m = create_base_map()
    
    # Добавляем точки на карту
    m = add_points_to_map(m, df)
    
    # Добавляем тепловую карту по скорости
    m = add_heatmap_to_map(m, df, heatmap_type='speed')
    
    # Добавляем тепловую карту по плотности
    m = add_heatmap_to_map(m, df, heatmap_type='density')
    
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
                          charts=charts)

# Маршрут для страницы аналитики
@app.route('/analytics')
def analytics():
    # Получаем статистику
    stats = get_statistics(df)
    
    # Создаем графики
    charts = create_charts(df, stats)
    
    return render_template('analytics.html', 
                          stats=stats,
                          charts=charts)

# Маршрут для получения отфильтрованной карты
@app.route('/get_map')
def get_map():
    # Получаем параметры фильтрации
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))
    map_type = request.args.get('map_type', 'points')
    
    # Создаем базовую карту
    m = create_base_map()
    
    # В зависимости от типа карты добавляем соответствующие слои
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
    filtered_df = df.copy()
    
    # Определяем колонку скорости в зависимости от провайдера
    if provider != 'all':
        if provider == 'kt':
            filtered_df = filtered_df[filtered_df['kt_speedtest'] == 1]
            speed_column = 'kt_download_speed'
        elif provider == 'beeline':
            filtered_df = filtered_df[filtered_df['beeline_speedtest'] == 1]
            speed_column = 'beeline_download_speed'
        elif provider == 'almatv':
            filtered_df = filtered_df[filtered_df['almatv_speedtest'] == 1]
            speed_column = 'almatv_download_speed'
    else:
        # Для всех провайдеров используем максимальную скорость из доступных
        filtered_df['max_download_speed'] = filtered_df[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'
    
    # Фильтруем по скорости
    filtered_df = filtered_df[(filtered_df[speed_column] >= min_speed) & 
                             (filtered_df[speed_column] <= max_speed)]
    
    # Получаем статистику
    stats = get_statistics(filtered_df)
    
    # Возвращаем статистику в формате JSON
    return jsonify(stats)

# Маршрут для получения обновленных графиков
@app.route('/get_charts')
def get_charts():
    # Получаем параметры фильтрации
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))
    
    # Фильтруем данные
    filtered_df = df.copy()
    
    # Определяем колонку скорости в зависимости от провайдера
    if provider != 'all':
        if provider == 'kt':
            filtered_df = filtered_df[filtered_df['kt_speedtest'] == 1]
            speed_column = 'kt_download_speed'
        elif provider == 'beeline':
            filtered_df = filtered_df[filtered_df['beeline_speedtest'] == 1]
            speed_column = 'beeline_download_speed'
        elif provider == 'almatv':
            filtered_df = filtered_df[filtered_df['almatv_speedtest'] == 1]
            speed_column = 'almatv_download_speed'
    else:
        # Для всех провайдеров используем максимальную скорость из доступных
        filtered_df['max_download_speed'] = filtered_df[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'
    
    # Фильтруем по скорости
    filtered_df = filtered_df[(filtered_df[speed_column] >= min_speed) & 
                             (filtered_df[speed_column] <= max_speed)]
    
    # Получаем статистику
    stats = get_statistics(filtered_df)
    
    # Создаем графики
    charts = create_charts(filtered_df, stats, filtered=True)
    
    # Возвращаем графики в формате JSON
    return jsonify(charts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
