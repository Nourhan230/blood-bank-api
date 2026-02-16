import sqlite3
import pandas as pd
from datetime import datetime , timedelta


class AnalyticsEngine:

    def __init__(self , db_path='data/database.db'):
        self.db_path = db_path

    def calculate_waste_rates(self , hospital_id=None , blood_type=None , start_date=None , end_date=None):
        """Calculate blood waste rates"""

        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT 
                hospital_id,
                blood_type,
                SUM(units_collected) as total_collected,
                SUM(units_used) as total_used,
                SUM(units_expired) as total_expired
            FROM inventory_movements
            WHERE 1=1
        """
        params = []

        if hospital_id:
            query += " AND hospital_id = ?"
            params.append(hospital_id)
        if blood_type:
            query += " AND blood_type = ?"
            params.append(blood_type)
        if start_date:
            query += " AND movement_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND movement_date <= ?"
            params.append(end_date)

        query += " GROUP BY hospital_id, blood_type"

        df = pd.read_sql(query , conn , params=params if params else None)
        conn.close()

        if df.empty:
            return {
                'waste_rates': [] ,
                'overall_waste_rate': 0.0 ,
                'recommendations': []
            }

        # Calculate waste rates
        df['waste_rate'] = df['total_expired'] / (df['total_collected'] + 1)  # +1 to avoid division by zero
        df['waste_rate'] = df['waste_rate'].fillna(0)

        # Assign status
        def get_status(rate):
            if rate < 0.05:
                return 'LOW'
            elif rate < 0.10:
                return 'ACCEPTABLE'
            elif rate < 0.20:
                return 'HIGH'
            else:
                return 'CRITICAL'

        df['status'] = df['waste_rate'].apply(get_status)

        waste_rates = []
        for _ , row in df.iterrows():
            waste_rates.append({
                'hospital_id': row['hospital_id'] ,
                'blood_type': row['blood_type'] ,
                'waste_rate': round(row['waste_rate'] , 3) ,
                'units_expired': int(row['total_expired']) ,
                'total_units': int(row['total_collected']) ,
                'status': row['status']
            })

        overall_rate = df['total_expired'].sum() / (df['total_collected'].sum() + 1)

        # Generate recommendations
        recommendations = self._generate_waste_recommendations(df)

        return {
            'waste_rates': waste_rates ,
            'overall_waste_rate': round(overall_rate , 3) ,
            'total_expired_units': int(df['total_expired'].sum()) ,
            'total_collected_units': int(df['total_collected'].sum()) ,
            'recommendations': recommendations
        }

    def forecast_demand(self , hospital_id=None , blood_type=None , days=30):
        """Forecast blood demand for next N days"""

        conn = sqlite3.connect(self.db_path)

        # Get historical usage
        query = """
            SELECT 
                hospital_id,
                blood_type,
                AVG(units_used) as avg_daily_demand,
                COUNT(*) as days_of_data,
                MAX(units_used) as peak_usage
            FROM blood_usage_history
            WHERE date_of_usage >= date('now', '-90 days')
        """
        params = []

        if hospital_id:
            query += " AND hospital_id = ?"
            params.append(hospital_id)
        if blood_type:
            query += " AND blood_type = ?"
            params.append(blood_type)

        query += " GROUP BY hospital_id, blood_type"

        df = pd.read_sql(query , conn , params=params if params else None)

        # Get events that might affect demand
        events_query = """
            SELECT * FROM events
            WHERE event_date BETWEEN date('now') AND date('now', '+30 days')
        """
        events_df = pd.read_sql(events_query , conn)

        conn.close()

        forecasts = []
        for _ , row in df.iterrows():
            base_forecast = row['avg_daily_demand'] * days

            # Adjust for events
            event_adjustment = 0
            for _ , event in events_df.iterrows():
                event_adjustment += row['avg_daily_demand'] * (event['impact_level'] - 1.0)

            total_forecast = base_forecast + event_adjustment

            # Determine trend (simplified)
            trend = self._calculate_trend(row['hospital_id'] , row['blood_type'])

            forecasts.append({
                'hospital_id': row['hospital_id'] ,
                'blood_type': row['blood_type'] ,
                'avg_daily_demand': round(row['avg_daily_demand'] , 2) ,
                f'next_{days}_days_forecast': round(total_forecast , 1) ,
                'demand_trend': trend ,
                'peak_days': [] ,  # Would calculate from historical data
                'confidence_level': 0.85 if row['days_of_data'] > 60 else 0.65
            })

        return forecasts

    def generate_heatmap(self , bounds=None , blood_type=None):
        """Generate geographic risk heatmap data"""

        conn = sqlite3.connect(self.db_path)

        # This is a simplified version
        # In production, you'd use clustering algorithms

        query = """
            SELECT 
                i.hospital_id,
                i.blood_type,
                i.current_units,
                30.0444 + (RANDOM() * 0.1) as lat,
                31.2357 + (RANDOM() * 0.1) as lng
            FROM blood_inventory i
        """

        hospitals_df = pd.read_sql(query , conn)

        # Get donor counts by area
        donors_query = "SELECT location_lat as lat, location_lng as lng FROM donors WHERE is_available = 1"
        donors_df = pd.read_sql(donors_query , conn)

        conn.close()

        # Create grid of areas and calculate risk
        areas = []

        # Simplified: Create areas based on hospital locations
        for _ , hospital in hospitals_df.iterrows():
            demand_score = max(0.1 , 1.0 - (hospital['current_units'] / 50))

            # Count nearby donors (simplified)
            donor_density = len(donors_df)  # Simplified

            # Determine risk level
            if demand_score >= 0.9 or donor_density < 5:
                risk_level = 'CRITICAL'
            elif demand_score >= 0.75 or donor_density < 10:
                risk_level = 'HIGH'
            elif demand_score >= 0.5:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'

            areas.append({
                'area_id': f"AREA_{hospital['hospital_id']}" ,
                'location': {
                    'latitude': hospital['lat'] ,
                    'longitude': hospital['lng']
                } ,
                'demand_score': round(demand_score , 2) ,
                'donor_density': donor_density ,
                'risk_level': risk_level ,
                'hospital_id': hospital['hospital_id']
            })

        high_risk_count = len([a for a in areas if a['risk_level'] in ['HIGH' , 'CRITICAL']])

        return {
            'areas': areas ,
            'metadata': {
                'total_areas': len(areas) ,
                'high_risk_areas': high_risk_count ,
                'generated_at': datetime.now().isoformat()
            }
        }

    def _calculate_trend(self , hospital_id , blood_type):
        """Calculate demand trend (INCREASING, STABLE, DECREASING)"""
        # Simplified version
        # In production, use linear regression on historical data
        return 'STABLE'  # Placeholder

    def _generate_waste_recommendations(self , df):
        """Generate recommendations to reduce waste"""
        recommendations = []

        high_waste = df[df['waste_rate'] > 0.15]

        if not high_waste.empty:
            for _ , row in high_waste.iterrows():
                recommendations.append(
                    f"High waste rate ({row['waste_rate']:.1%}) for {row['blood_type']} at {row['hospital_id']}. "
                    f"Consider reducing collection or improving inventory rotation."
                )

        if df['waste_rate'].mean() > 0.10:
            recommendations.append(
                "Overall waste rate is above acceptable threshold. Review inventory management practices.")

        return recommendations if recommendations else ["Waste rates are within acceptable limits."]