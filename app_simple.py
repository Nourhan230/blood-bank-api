from flask import Flask , jsonify , request
from flask_cors import CORS
from datetime import datetime , timedelta

app = Flask(__name__)
CORS(app)

# Sample data for demo
SAMPLE_RISKS = [
    {
        'hospital_id': 'H001' ,
        'blood_type': 'O+' ,
        'risk_score': 0.85 ,
        'risk_level': 'HIGH' ,
        'days_to_shortage': 5 ,
        'current_units': 15 ,
        'expected_shortage_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
    } ,
    {
        'hospital_id': 'H001' ,
        'blood_type': 'O-' ,
        'risk_score': 0.92 ,
        'risk_level': 'CRITICAL' ,
        'days_to_shortage': 2 ,
        'current_units': 8 ,
        'expected_shortage_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    } ,
    {
        'hospital_id': 'H002' ,
        'blood_type': 'A+' ,
        'risk_score': 0.45 ,
        'risk_level': 'MEDIUM' ,
        'days_to_shortage': 12 ,
        'current_units': 28 ,
        'expected_shortage_date': (datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d')
    } ,
]

SAMPLE_INVENTORY = [
    {'hospital_id': 'H001' , 'blood_type': 'O+' , 'current_units': 45} ,
    {'hospital_id': 'H001' , 'blood_type': 'A+' , 'current_units': 32} ,
    {'hospital_id': 'H001' , 'blood_type': 'O-' , 'current_units': 8} ,
    {'hospital_id': 'H002' , 'blood_type': 'B+' , 'current_units': 28} ,
]


@app.route('/api/health' , methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy' ,
        'message': 'Blood Bank API is running' ,
        'timestamp': datetime.now().isoformat() ,
        'version': '1.0.0'
    }) , 200


@app.route('/api/v1/predict/risks' , methods=['GET'])
def get_risks():
    risk_level = request.args.get('risk_level')

    risks = SAMPLE_RISKS.copy()
    if risk_level:
        risks = [r for r in risks if r['risk_level'] == risk_level.upper()]

    return jsonify({
        'status': 'success' ,
        'risks': risks ,
        'total_count': len(risks) ,
        'timestamp': datetime.now().isoformat()
    }) , 200


@app.route('/api/v1/inventory' , methods=['GET'])
def get_inventory():
    return jsonify({
        'status': 'success' ,
        'inventory': SAMPLE_INVENTORY ,
        'total_count': len(SAMPLE_INVENTORY) ,
        'timestamp': datetime.now().isoformat()
    }) , 200


@app.route('/api/v1/match/emergency' , methods=['POST'])
def match_emergency():
    data = request.get_json()

    # Sample matched donors
    matched_donors = [
        {
            'donor_id': 'D001' ,
            'blood_type': data.get('blood_type_needed' , 'O+') ,
            'matching_score': 0.95 ,
            'distance_km': 1.2
        } ,
        {
            'donor_id': 'D002' ,
            'blood_type': data.get('blood_type_needed' , 'O+') ,
            'matching_score': 0.88 ,
            'distance_km': 2.5
        }
    ]

    return jsonify({
        'status': 'success' ,
        'request_id': f"REQ{datetime.now().strftime('%Y%m%d%H%M%S')}" ,
        'matched_donors': matched_donors ,
        'total_matches': len(matched_donors) ,
        'timestamp': datetime.now().isoformat()
    }) , 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error' , 'message': 'Endpoint not found'}) , 404


if __name__ == '__main__':
    import os

    port = int(os.environ.get('PORT' , 8080))
    print(f"🩸 Blood Bank API running on port {port}")
    app.run(host='0.0.0.0' , port=port , debug=False)