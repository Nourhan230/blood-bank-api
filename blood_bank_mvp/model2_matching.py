import sqlite3
import pandas as pd
from datetime import datetime
from math import radians , sin , cos , sqrt , atan2


class MatchingEngine:

    def __init__(self , db_path='data/database.db'):
        self.db_path = db_path

    def match_donors(self , hospital_id , blood_type , units_needed , hospital_location , urgency_level):
        """
        Match donors to emergency request

        Algorithm:
        1. Find compatible blood type donors
        2. Calculate distance from hospital
        3. Check donor availability (last donation > 56 days ago)
        4. Calculate matching score based on:
           - Distance (closer = better)
           - Days since last donation (longer = better)
           - Blood type compatibility (exact match = best)
        5. Rank by matching score
        """

        conn = sqlite3.connect(self.db_path)

        # Get compatible donors
        compatible_types = self._get_compatible_blood_types(blood_type)

        query = f"""
            SELECT * FROM donors
            WHERE blood_type IN ({','.join(['?'] * len(compatible_types))})
            AND is_available = 1
        """

        donors_df = pd.read_sql(query , conn , params=compatible_types)
        conn.close()

        if donors_df.empty:
            return {
                'request_id': self._generate_request_id() ,
                'matched_donors': [] ,
                'total_matches': 0 ,
                'message': 'No available donors found'
            }

        # Calculate distances and matching scores
        hospital_lat = hospital_location['latitude']
        hospital_lng = hospital_location['longitude']

        donors_df['distance_km'] = donors_df.apply(
            lambda row: self._haversine_distance(
                hospital_lat , hospital_lng ,
                row['location_lat'] , row['location_lng']
            ) ,
            axis=1
        )

        # Calculate matching score
        donors_df['matching_score'] = donors_df.apply(
            lambda row: self._calculate_matching_score(
                row['blood_type'] , blood_type ,
                row['distance_km'] ,
                row['last_donation_date'] ,
                urgency_level
            ) ,
            axis=1
        )

        # Sort by matching score and get top matches
        donors_df = donors_df.sort_values('matching_score' , ascending=False)
        top_donors = donors_df.head(min(10 , units_needed * 2))  # Get 2x needed units

        matched_donors = []
        for _ , donor in top_donors.iterrows():
            matched_donors.append({
                'donor_id': donor['donor_id'] ,
                'blood_type': donor['blood_type'] ,
                'matching_score': round(donor['matching_score'] , 2) ,
                'distance_km': round(donor['distance_km'] , 2) ,
                'location': {
                    'latitude': donor['location_lat'] ,
                    'longitude': donor['location_lng']
                } ,
                'last_donation_date': donor['last_donation_date'] ,
                'is_available': bool(donor['is_available'])
            })

        return {
            'request_id': self._generate_request_id() ,
            'matched_donors': matched_donors ,
            'total_matches': len(matched_donors) ,
            'urgency_level': urgency_level
        }

    def search_donors(self , blood_type=None , location=None , radius_km=10 , is_available=None):
        """Search for donors with filters"""

        conn = sqlite3.connect(self.db_path)

        query = "SELECT * FROM donors WHERE 1=1"
        params = []

        if blood_type:
            query += " AND blood_type = ?"
            params.append(blood_type)

        if is_available is not None:
            query += " AND is_available = ?"
            params.append(1 if is_available else 0)

        donors_df = pd.read_sql(query , conn , params=params if params else None)
        conn.close()

        if location and not donors_df.empty:
            lat , lng = location
            donors_df['distance_km'] = donors_df.apply(
                lambda row: self._haversine_distance(
                    lat , lng , row['location_lat'] , row['location_lng']
                ) ,
                axis=1
            )
            donors_df = donors_df[donors_df['distance_km'] <= radius_km]

        return donors_df.to_dict('records')

    def _haversine_distance(self , lat1 , lon1 , lat2 , lon2):
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth radius in kilometers

        lat1 , lon1 , lat2 , lon2 = map(radians , [lat1 , lon1 , lat2 , lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a) , sqrt(1 - a))

        return R * c

    def _calculate_matching_score(self , donor_blood_type , needed_blood_type , distance , last_donation , urgency):
        """
        Calculate matching score (0-1)

        Factors:
        - Blood type match (40% weight)
        - Distance (30% weight)
        - Days since donation (20% weight)
        - Urgency adjustment (10% weight)
        """

        # Blood type score
        if donor_blood_type == needed_blood_type:
            blood_score = 1.0
        elif donor_blood_type in self._get_compatible_blood_types(needed_blood_type):
            blood_score = 0.7
        else:
            blood_score = 0.0

        # Distance score (closer = better)
        if distance <= 5:
            distance_score = 1.0
        elif distance <= 10:
            distance_score = 0.7
        elif distance <= 20:
            distance_score = 0.4
        else:
            distance_score = max(0.1 , 1.0 - (distance / 100))

        # Days since donation score (longer = better)
        try:
            last_date = datetime.strptime(last_donation , '%Y-%m-%d')
            days_since = (datetime.now() - last_date).days

            if days_since >= 90:
                donation_score = 1.0
            elif days_since >= 56:  # Minimum safe period
                donation_score = 0.8
            else:
                donation_score = 0.3  # Can donate but not ideal
        except:
            donation_score = 0.5

        # Urgency adjustment
        urgency_multiplier = {
            'CRITICAL': 1.2 ,
            'HIGH': 1.1 ,
            'MEDIUM': 1.0 ,
            'LOW': 0.9
        }.get(urgency , 1.0)

        # Weighted score
        score = (
                        blood_score * 0.4 +
                        distance_score * 0.3 +
                        donation_score * 0.2 +
                        0.1
                ) * urgency_multiplier

        return min(score , 1.0)  # Cap at 1.0

    def _get_compatible_blood_types(self , blood_type):
        """Get list of compatible blood types that can donate to the given type"""
        compatibility = {
            'O-': ['O-'] ,
            'O+': ['O-' , 'O+'] ,
            'A-': ['O-' , 'A-'] ,
            'A+': ['O-' , 'O+' , 'A-' , 'A+'] ,
            'B-': ['O-' , 'B-'] ,
            'B+': ['O-' , 'O+' , 'B-' , 'B+'] ,
            'AB-': ['O-' , 'A-' , 'B-' , 'AB-'] ,
            'AB+': ['O-' , 'O+' , 'A-' , 'A+' , 'B-' , 'B+' , 'AB-' , 'AB+']
        }
        return compatibility.get(blood_type , [blood_type])

    def _generate_request_id(self):
        """Generate unique request ID"""
        return f"REQ{datetime.now().strftime('%Y%m%d%H%M%S')}"