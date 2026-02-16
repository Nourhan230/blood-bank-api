from flask import Flask , jsonify , request
from flask_cors import CORS
from datetime import datetime
import sqlite3

# Import your model logic (we'll create these next)
from blood_bank_mvp.model1_prediction import PredictionEngine
from blood_bank_mvp.model2_matching import MatchingEngine
from blood_bank_mvp.model3_analytics import AnalyticsEngine

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow frontend to call your API

# Initialize model engines
prediction_engine = PredictionEngine()
matching_engine = MatchingEngine()
analytics_engine = AnalyticsEngine()


# ============================================
# HEALTH CHECK ENDPOINT (Test if API is running)
# ============================================

@app.route('/api/health' , methods=['GET'])
def health_check():
    """Check if API is running"""
    return jsonify({
        'status': 'healthy' ,
        'message': 'Blood Bank API is running' ,
        'timestamp': datetime.now().isoformat() ,
        'version': '1.0.0'
    }) , 200


# ============================================
# MODEL 1: PREDICTIVE DEMAND ENGINE
# ============================================

@app.route('/api/v1/predict/shortage' , methods=['POST'])
def predict_shortage():
    """
    Predict blood shortages

    Request Body (optional):
    {
        "hospital_id": "H001",  // optional - filter by hospital
        "blood_type": "O+"      // optional - filter by blood type
    }

    Response:
    {
        "status": "success",
        "predictions": [
            {
                "hospital_id": "H001",
                "blood_type": "O+",
                "risk_score": 0.85,
                "risk_level": "HIGH",
                "expected_shortage_date": "2024-02-20",
                "days_to_shortage": 5,
                "current_units": 15,
                "avg_daily_usage": 3.0
            }
        ],
        "timestamp": "2024-02-15T10:00:00"
    }
    """
    try:
        data = request.get_json() if request.is_json else {}
        hospital_id = data.get('hospital_id')
        blood_type = data.get('blood_type')

        # Call your prediction model
        predictions = prediction_engine.predict_shortages(hospital_id , blood_type)

        return jsonify({
            'status': 'success' ,
            'predictions': predictions ,
            'total_predictions': len(predictions) ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


@app.route('/api/v1/predict/risks' , methods=['GET'])
def get_risks():
    """
    Get current risk predictions with filters

    Query Parameters:
    - hospital_id: Filter by hospital (optional)
    - blood_type: Filter by blood type (optional)
    - risk_level: Filter by risk level (LOW/MEDIUM/HIGH/CRITICAL) (optional)

    Example: /api/v1/predict/risks?risk_level=CRITICAL&blood_type=O-

    Response: Same as predict_shortage
    """
    try:
        hospital_id = request.args.get('hospital_id')
        blood_type = request.args.get('blood_type')
        risk_level = request.args.get('risk_level')

        predictions = prediction_engine.predict_shortages(hospital_id , blood_type)

        # Filter by risk level if provided
        if risk_level:
            predictions = [p for p in predictions if p['risk_level'] == risk_level.upper()]

        return jsonify({
            'status': 'success' ,
            'risks': predictions ,
            'total_count': len(predictions) ,
            'filters': {
                'hospital_id': hospital_id ,
                'blood_type': blood_type ,
                'risk_level': risk_level
            } ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


# ============================================
# MODEL 2: DYNAMIC DONOR MATCHING
# ============================================

@app.route('/api/v1/match/emergency' , methods=['POST'])
def match_emergency():
    """
    Match donors for emergency blood request

    Request Body:
    {
        "hospital_id": "H001",
        "blood_type_needed": "O+",
        "units_needed": 5,
        "location": {
            "latitude": 30.0444,
            "longitude": 31.2357
        },
        "urgency_level": "CRITICAL"  // LOW, MEDIUM, HIGH, CRITICAL
    }

    Response:
    {
        "status": "success",
        "request_id": "REQ20240215100000",
        "matched_donors": [
            {
                "donor_id": "D001",
                "blood_type": "O+",
                "matching_score": 0.95,
                "distance_km": 1.2,
                "location": {
                    "latitude": 30.0500,
                    "longitude": 31.2400
                },
                "last_donation_date": "2023-12-10",
                "is_available": true
            }
        ],
        "total_matches": 5
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required = ['hospital_id' , 'blood_type_needed' , 'units_needed' , 'location' , 'urgency_level']
        for field in required:
            if field not in data:
                return jsonify({
                    'status': 'error' ,
                    'message': f'Missing required field: {field}'
                }) , 400

        # Call matching engine
        result = matching_engine.match_donors(
            hospital_id=data['hospital_id'] ,
            blood_type=data['blood_type_needed'] ,
            units_needed=data['units_needed'] ,
            hospital_location=data['location'] ,
            urgency_level=data['urgency_level']
        )

        return jsonify({
            'status': 'success' ,
            **result ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


@app.route('/api/v1/match/donors' , methods=['GET'])
def search_donors():
    """
    Search available donors by criteria

    Query Parameters:
    - blood_type: Filter by blood type (optional)
    - latitude: Center latitude for location search (optional)
    - longitude: Center longitude for location search (optional)
    - radius_km: Search radius in km (default: 10)
    - is_available: Filter by availability (true/false) (optional)

    Example: /api/v1/match/donors?blood_type=O+&latitude=30.04&longitude=31.23&radius_km=5
    """
    try:
        blood_type = request.args.get('blood_type')
        latitude = request.args.get('latitude' , type=float)
        longitude = request.args.get('longitude' , type=float)
        radius_km = request.args.get('radius_km' , 10 , type=float)
        is_available = request.args.get('is_available' , type=str)

        donors = matching_engine.search_donors(
            blood_type=blood_type ,
            location=(latitude , longitude) if latitude and longitude else None ,
            radius_km=radius_km ,
            is_available=is_available == 'true' if is_available else None
        )

        return jsonify({
            'status': 'success' ,
            'donors': donors ,
            'total_count': len(donors) ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


# ============================================
# MODEL 3: ANALYTICS ENGINE
# ============================================

@app.route('/api/v1/analytics/waste' , methods=['GET'])
def get_waste_analysis():
    """
    Get waste rate analysis

    Query Parameters:
    - hospital_id: Filter by hospital (optional)
    - blood_type: Filter by blood type (optional)
    - start_date: Start date YYYY-MM-DD (optional)
    - end_date: End date YYYY-MM-DD (optional)

    Response:
    {
        "status": "success",
        "waste_rates": [
            {
                "hospital_id": "H001",
                "blood_type": "O+",
                "waste_rate": 0.06,
                "units_expired": 15,
                "total_units": 250,
                "status": "ACCEPTABLE"
            }
        ],
        "overall_waste_rate": 0.08,
        "recommendations": [...]
    }
    """
    try:
        hospital_id = request.args.get('hospital_id')
        blood_type = request.args.get('blood_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        result = analytics_engine.calculate_waste_rates(
            hospital_id=hospital_id ,
            blood_type=blood_type ,
            start_date=start_date ,
            end_date=end_date
        )

        return jsonify({
            'status': 'success' ,
            **result ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


@app.route('/api/v1/analytics/forecast' , methods=['GET'])
def get_demand_forecast():
    """
    Get demand forecast

    Query Parameters:
    - hospital_id: Filter by hospital (optional)
    - blood_type: Filter by blood type (optional)
    - days: Number of days to forecast (default: 30)

    Response:
    {
        "status": "success",
        "forecasts": [
            {
                "hospital_id": "H001",
                "blood_type": "O+",
                "avg_daily_demand": 11.4,
                "next_30_days_forecast": 385.0,
                "demand_trend": "INCREASING",
                "peak_days": [...]
            }
        ]
    }
    """
    try:
        hospital_id = request.args.get('hospital_id')
        blood_type = request.args.get('blood_type')
        days = request.args.get('days' , 30 , type=int)

        forecasts = analytics_engine.forecast_demand(
            hospital_id=hospital_id ,
            blood_type=blood_type ,
            days=days
        )

        return jsonify({
            'status': 'success' ,
            'forecasts': forecasts ,
            'forecast_period_days': days ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


@app.route('/api/v1/analytics/heatmap' , methods=['GET'])
def get_heatmap():
    """
    Get geographic risk heatmap data

    Query Parameters:
    - min_lat, min_lng, max_lat, max_lng: Bounding box coordinates
    - blood_type: Filter by blood type (optional)

    Example: /api/v1/analytics/heatmap?min_lat=30.0&min_lng=31.0&max_lat=30.1&max_lng=31.5

    Response:
    {
        "status": "success",
        "areas": [
            {
                "area_id": "AREA_001",
                "location": {"latitude": 30.0444, "longitude": 31.2357},
                "demand_score": 0.85,
                "donor_density": 12.5,
                "risk_level": "MEDIUM"
            }
        ],
        "metadata": {
            "total_areas": 10,
            "high_risk_areas": 2
        }
    }
    """
    try:
        min_lat = request.args.get('min_lat' , type=float)
        min_lng = request.args.get('min_lng' , type=float)
        max_lat = request.args.get('max_lat' , type=float)
        max_lng = request.args.get('max_lng' , type=float)
        blood_type = request.args.get('blood_type')

        heatmap_data = analytics_engine.generate_heatmap(
            bounds=(min_lat , min_lng , max_lat , max_lng) if all([min_lat , min_lng , max_lat , max_lng]) else None ,
            blood_type=blood_type
        )

        return jsonify({
            'status': 'success' ,
            **heatmap_data ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


# ============================================
# INVENTORY MANAGEMENT (BONUS)
# ============================================

@app.route('/api/v1/inventory' , methods=['GET'])
def get_inventory():
    """Get current blood inventory"""
    try:
        hospital_id = request.args.get('hospital_id')
        blood_type = request.args.get('blood_type')

        conn = sqlite3.connect('data/database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM blood_inventory WHERE 1=1"
        params = []

        if hospital_id:
            query += " AND hospital_id = ?"
            params.append(hospital_id)
        if blood_type:
            query += " AND blood_type = ?"
            params.append(blood_type)

        cursor.execute(query , params)
        inventory = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'status': 'success' ,
            'inventory': inventory ,
            'total_count': len(inventory) ,
            'timestamp': datetime.now().isoformat()
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


@app.route('/api/v1/inventory/update' , methods=['POST'])
def update_inventory():
    """
    Update blood inventory

    Request Body:
    {
        "hospital_id": "H001",
        "blood_type": "O+",
        "current_units": 45
    }
    """
    try:
        data = request.get_json()

        conn = sqlite3.connect('data/database.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO blood_inventory (hospital_id, blood_type, current_units, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(hospital_id, blood_type) 
            DO UPDATE SET current_units = ?, last_updated = ?
        """ , (
            data['hospital_id'] ,
            data['blood_type'] ,
            data['current_units'] ,
            datetime.now().isoformat() ,
            data['current_units'] ,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'status': 'success' ,
            'message': 'Inventory updated successfully' ,
            'updated': data
        }) , 200

    except Exception as e:
        return jsonify({
            'status': 'error' ,
            'message': str(e)
        }) , 500


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'status': 'error' ,
        'message': 'Endpoint not found' ,
        'code': 404
    }) , 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'status': 'error' ,
        'message': 'Internal server error' ,
        'code': 500
    }) , 500


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    import os

    print("🩸 Blood Bank API Server Starting...")

    # Get port from environment variable (Railway uses PORT)
    port = int(os.environ.get('PORT' , 5000))

    print(f"📍 Running on port: {port}")
    print("📚 API Documentation: See API_DOCUMENTATION.md")
    print("🏥 Health Check: http://localhost:{port}/api/health")
    print("\n✅ Ready to receive requests!\n")

    app.run(
        host='0.0.0.0' ,  # Allow external connections
        port=port ,
        debug=False  # Production mode
    )