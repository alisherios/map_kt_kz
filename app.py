import pandas as pd
import folium
from folium.plugins import HeatMap
from flask import Flask, render_template, request

app = Flask(__name__)

# Загрузка данных
try:
    df = pd.read_excel('data/cbm_st_pro_1.xlsx')
    print(f"Данные загружены успешно. Количество строк: {len(df)}")
    print("Первые 5 строк DataFrame:")
    print(df.head())
    print("\nПропуски в координатах и скоростях:")
    print(df[['latitude_speedtest', 'longitude_speedtest', 'kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].isna().sum())
    print("\nСтатистика по скоростям:")
    print(df[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].describe())
    print("\nЗначения провайдеров:")
    print(df[['kt_speedtest', 'beeline_speedtest', 'almatv_speedtest']].value_counts())
except Exception as e:
    print(f"Ошибка при загрузке данных: {e}")
    df = pd.DataFrame()

# Создание базовой карты
def create_base_map():
    m = folium.Map(location=[51.1605, 71.4704], zoom_start=12, tiles='CartoDB positron')
    return m

# Добавление точек на карту
def add_points_to_map(m, data, provider='all', min_speed=0, max_speed=500):
    if data.empty:
        print("Ошибка: данные пусты")
        folium.Marker(
            location=[51.1605, 71.4704],
            popup="Ошибка загрузки данных. Пожалуйста, проверьте формат данных.",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)
        return m
    
    filtered_data = data.copy()
    filtered_data = filtered_data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    print(f"После удаления NaN координат: {len(filtered_data)} строк")
    
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
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'
        print(f"Значения max_download_speed: {filtered_data['max_download_speed'].describe()}")
    
    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & 
                                 (filtered_data[speed_column] <= max_speed)]
    print(f"После фильтрации по скорости: {len(filtered_data)} строк")
    
    if len(filtered_data) == 0:
        print("Нет данных после фильтрации")
        folium.Marker(
            location=[51.1605, 71.4704],
            popup="Нет данных, соответствующих выбранным фильтрам",
            icon=folium.Icon(color="orange", icon="info-sign")
        ).add_to(m)
        return m
    
    kt_group = folium.FeatureGroup(name='Казахтелеком', show=True)
    beeline_group = folium.FeatureGroup(name='Beeline', show=True)
    almatv_group = folium.FeatureGroup(name='AlmaTV', show=True)
    
    for _, row in filtered_data.iterrows():
        if provider != 'all':
            current_speed = row[speed_column]
        else:
            current_speed = row['max_download_speed']
            
        if current_speed < 50:
            color = 'red'
        elif current_speed < 100:
            color = 'orange'
        else:
            color = 'green'
        
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
        
        popup = folium.Popup(popup_html, max_width=300)
        
        if row['kt_speedtest'] == 1:
            folium.Marker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                icon=folium.Icon(color=color)
            ).add_to(kt_group)
        
        if row['beeline_speedtest'] == 1:
            folium.Marker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                icon=folium.Icon(color=color)
            ).add_to(beeline_group)
        
        if row['almatv_speedtest'] == 1:
            folium.Marker(
                location=[row['latitude_speedtest'], row['longitude_speedtest']],
                popup=popup,
                tooltip=f"Скорость: {current_speed:.1f} Мбит/с",
                icon=folium.Icon(color=color)
            ).add_to(almatv_group)
    
    kt_group.add_to(m)
    beeline_group.add_to(m)
    almatv_group.add_to(m)
    
    print(f"Добавлено маркеров Казахтелеком: {len(filtered_data[filtered_data['kt_speedtest'] == 1])}")
    print(f"Добавлено маркеров Beeline: {len(filtered_data[filtered_data['beeline_speedtest'] == 1])}")
    print(f"Добавлено маркеров AlmaTV: {len(filtered_data[filtered_data['almatv_speedtest'] == 1])}")
    
    return m

# Добавление тепловой карты
def add_heatmap_to_map(m, data, map_type='heatmap_speed', provider='all', min_speed=0, max_speed=500):
    if data.empty:
        print("Ошибка: данные для тепловой карты пусты")
        folium.Marker(
            location=[51.1605, 71.4704],
            popup="Ошибка загрузки данных для тепловой карты.",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)
        return m

    filtered_data = data.copy()
    filtered_data = filtered_data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])
    print(f"После удаления NaN координат для тепловой карты: {len(filtered_data)} строк")

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
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'
        print(f"Значения max_download_speed для тепловой карты: {filtered_data['max_download_speed'].describe()}")

    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & 
                                 (filtered_data[speed_column] <= max_speed)]
    print(f"После фильтрации по скорости для тепловой карты: {len(filtered_data)} строк")

    if len(filtered_data) == 0:
        print("Нет данных после фильтрации для тепловой карты")
        folium.Marker(
            location=[51.1605, 71.4704],
            popup="Нет данных для тепловой карты, соответствующих фильтрам",
            icon=folium.Icon(color="orange", icon="info-sign")
        ).add_to(m)
        return m

    if map_type == 'heatmap_speed':
        heat_data = []
        for _, row in filtered_data.iterrows():
            weight = row[speed_column] / filtered_data[speed_column].max() if filtered_data[speed_column].max() > 0 else 0
            heat_data.append([row['latitude_speedtest'], row['longitude_speedtest'], weight])
        print(f"Данные для тепловой карты по скорости: {len(heat_data)} точек")
        HeatMap(heat_data, radius=15, blur=10, max_zoom=13, name="Тепловая карта по скорости").add_to(m)
    elif map_type == 'heatmap_density':
        heat_data = [[row['latitude_speedtest'], row['longitude_speedtest']] for _, row in filtered_data.iterrows()]
        print(f"Данные для тепловой карты по плотности: {len(heat_data)} точек")
        HeatMap(heat_data, radius=15, blur=10, max_zoom=13, name="Тепловая карта по плотности").add_to(m)

    return m

# Главная страница
@app.route('/')
def index():
    m = create_base_map()
    m = add_points_to_map(m, df)  # Инициализация с точками по умолчанию
    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html)

# Получение отфильтрованной карты
@app.route('/get_map')
def get_map():
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))
    map_type = request.args.get('map_type', 'points')

    m = create_base_map()
    
    if map_type == 'points':
        m = add_points_to_map(m, df, provider=provider, min_speed=min_speed, max_speed=max_speed)
    elif map_type in ['heatmap_speed', 'heatmap_density']:
        m = add_heatmap_to_map(m, df, map_type=map_type, provider=provider, min_speed=min_speed, max_speed=max_speed)

    folium.LayerControl().add_to(m)  # Добавляем LayerControl после всех слоев
    return m._repr_html_()

# Получение статистики
@app.route('/get_stats')
def get_stats():
    provider = request.args.get('provider', 'all')
    min_speed = float(request.args.get('min_speed', 0))
    max_speed = float(request.args.get('max_speed', 500))

    filtered_data = df.copy()
    filtered_data = filtered_data.dropna(subset=['latitude_speedtest', 'longitude_speedtest'])

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
        filtered_data['max_download_speed'] = filtered_data[['kt_download_speed', 'beeline_download_speed', 'almatv_download_speed']].max(axis=1, skipna=True)
        speed_column = 'max_download_speed'

    filtered_data = filtered_data[(filtered_data[speed_column] >= min_speed) & 
                                 (filtered_data[speed_column] <= max_speed)]

    stats = {
        'total_points': len(filtered_data),
        'providers': {
            'kt': {
                'avg_download': filtered_data[filtered_data['kt_speedtest'] == 1][speed_column].mean() if not filtered_data[filtered_data['kt_speedtest'] == 1].empty else 0
            },
            'beeline': {
                'avg_download': filtered_data[filtered_data['beeline_speedtest'] == 1][speed_column].mean() if not filtered_data[filtered_data['beeline_speedtest'] == 1].empty else 0
            },
            'almatv': {
                'avg_download': filtered_data[filtered_data['almatv_speedtest'] == 1][speed_column].mean() if not filtered_data[filtered_data['almatv_speedtest'] == 1].empty else 0
            }
        }
    }
    print(f"Статистика: {stats}")
    return stats

if __name__ == '__main__':
    app.run(debug=True)
