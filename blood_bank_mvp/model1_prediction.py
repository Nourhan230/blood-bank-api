import sqlite3
import pandas as pd
from datetime import datetime , timedelta


class PredictionEngine:

    def __init__(self , db_path='data/database.db'):
        self.db_path = db_path

    def predict_shortages(self , hospital_id=None , blood_type=None):
        """
        Predict blood shortages using historical data and current inventory

        Algorithm:
        1. Get current inventory
        2. Calculate average daily usage (last 30 days)
        3. Calculate days until shortage: current_units / avg_daily_usage
        4. Assign risk score and level based on days remaining
        """

        conn = sqlite3.connect(self.db_path)

        # Get current inventory
        query_inventory = """
            SELECT hospital_id, blood_type, current_units
            FROM blood_inventory
            WHERE 1=1
        """
        params = []

        if hospital_id:
            query_inventory += " AND hospital_id = ?"
            params.append(hospital_id)
        if blood_type:
            query_inventory += " AND blood_type = ?"
            params.append(blood_type)

        inventory_df = pd.read_sql(query_inventory , conn , params=params if params else None)

        # Get historical usage (last 30 days average)
        query_usage = """
            SELECT 
                hospital_id, 
                blood_type, 
                AVG(units_used) as avg_daily_usage,
                COUNT(*) as days_of_data
            FROM blood_usage_history
            WHERE date_of_usage >= date('now', '-30 days')
        """

        if hospital_id:
            query_usage += " AND hospital_id = ?"
        if blood_type:
            query_usage += " AND blood_type = ?"

        query_usage += " GROUP BY hospital_id, blood_type"

        usage_df = pd.read_sql(query_usage , conn , params=params if params else None)

        conn.close()

        # Merge data
        merged = pd.merge(inventory_df , usage_df , on=['hospital_id' , 'blood_type'] , how='left')
        merged['avg_daily_usage'] = merged['avg_daily_usage'].fillna(0)

        # Calculate predictions
        predictions = []

        for _ , row in merged.iterrows():
            prediction = self._calculate_risk(
                current_units=row['current_units'] ,
                avg_daily_usage=row['avg_daily_usage'] ,
                hospital_id=row['hospital_id'] ,
                blood_type=row['blood_type']
            )
            predictions.append(prediction)

        return predictions

    def _calculate_risk(self , current_units , avg_daily_usage , hospital_id , blood_type):
        """Calculate risk score and level"""

        if avg_daily_usage == 0:
            avg_daily_usage = 1  # Prevent division by zero

        days_remaining = current_units / avg_daily_usage

        # Risk calculation logic
        if days_remaining <= 3:
            risk_score = min(0.90 + (3 - days_remaining) * 0.033 , 1.0)
            risk_level = "CRITICAL"
        elif days_remaining <= 7:
            risk_score = 0.60 + (7 - days_remaining) * 0.075
            risk_level = "HIGH"
        elif days_remaining <= 14:
            risk_score = 0.30 + (14 - days_remaining) * 0.043
            risk_level = "MEDIUM"
        else:
            risk_score = max(0.10 , min(0.30 , 30 / days_remaining))
            risk_level = "LOW"

        # Calculate expected shortage date
        if days_remaining < 30:
            shortage_date = (datetime.now() + timedelta(days=days_remaining)).strftime('%Y-%m-%d')
            days_to_shortage = int(days_remaining)
        else:
            shortage_date = None
            days_to_shortage = None

        return {
            'hospital_id': hospital_id ,
            'blood_type': blood_type ,
            'current_units': int(current_units) ,
            'avg_daily_usage': round(avg_daily_usage , 2) ,
            'risk_score': round(risk_score , 2) ,
            'risk_level': risk_level ,
            'expected_shortage_date': shortage_date ,
            'days_to_shortage': days_to_shortage
        }