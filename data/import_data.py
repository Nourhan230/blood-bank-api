import sqlite3
import json
import os


def create_database():
    """Create SQLite database and tables"""

    # أنشئ مجلد data لو مش موجود
    os.makedirs('data' , exist_ok=True)

    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()

    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS blood_inventory
                 (hospital_id TEXT, 
                  blood_type TEXT, 
                  current_units INTEGER,
                  last_updated TEXT,
                  PRIMARY KEY (hospital_id, blood_type))''')

    c.execute('''CREATE TABLE IF NOT EXISTS blood_usage_history
                 (hospital_id TEXT, 
                  blood_type TEXT, 
                  date_of_usage TEXT, 
                  units_used INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS donors
                 (donor_id TEXT PRIMARY KEY,
                  blood_type TEXT,
                  location_lat REAL,
                  location_lng REAL,
                  last_donation_date TEXT,
                  is_available INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS inventory_movements
                 (hospital_id TEXT,
                  blood_type TEXT,
                  units_collected INTEGER,
                  units_used INTEGER,
                  units_expired INTEGER,
                  movement_date TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (event_name TEXT,
                  event_date TEXT,
                  impact_level REAL,
                  description TEXT)''')

    conn.commit()
    conn.close()
    print("✅ Database created successfully!")


def import_json_data():
    """Import data from your JSON files"""

    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()


    base_path = r'C:\Users\Lenovo\PycharmProjects\PythonProject2\blood-bank-api\blood_bank_mvp'

    try:
        # Import inventory
        print("📥 Importing inventory data...")
        inventory_file = os.path.join(base_path ,'current_invent_m1.json')
        with open(inventory_file , encoding='utf-8') as f:
            data = json.load(f)
            for item in data['sample_data']:
                c.execute("""INSERT OR REPLACE INTO blood_inventory 
                             VALUES (?, ?, ?, datetime('now'))""" ,
                          (item['hospital_id'] , item['blood_type'] , item['current_units']))
        print("  ✅ Inventory imported")

        # Import usage history
        print("📥 Importing usage history...")
        usage_file = os.path.join(base_path ,'historical_m1.json')
        with open(usage_file , encoding='utf-8') as f:
            data = json.load(f)
            for item in data['sample_data']:
                c.execute("""INSERT INTO blood_usage_history VALUES (?, ?, ?, ?)""" ,
                          (item['hospital_id'] , item['blood_type'] ,
                           item['date_of_usage'] , item['units_used']))
        print("  ✅ Usage history imported")

        # Import donors
        print("📥 Importing donors...")
        donors_file = os.path.join(base_path ,'donor_listM2.json')
        with open(donors_file , encoding='utf-8') as f:
            data = json.load(f)
            for item in data['sample_data']:
                c.execute("""INSERT OR REPLACE INTO donors VALUES (?, ?, ?, ?, ?, ?)""" ,
                          (item['donor_id'] , item['blood_type'] ,
                           item['location']['latitude'] , item['location']['longitude'] ,
                           item['last_donation_date'] , 1 if item['is_available'] else 0))
        print("  ✅ Donors imported")

        # Import inventory movements
        print("📥 Importing inventory movements...")
        movements_file = os.path.join(base_path ,'waste_inventM3.json')
        with open(movements_file , encoding='utf-8') as f:
            data = json.load(f)
            for item in data['sample_data']:
                c.execute("""INSERT INTO inventory_movements VALUES (?, ?, ?, ?, ?, ?)""" ,
                          (item['hospital_id'] , item['blood_type'] ,
                           item['units_collected'] , item['units_used'] ,
                           item['units_expired'] , item['date']))
        print("  ✅ Inventory movements imported")

        # Import events
        print("📥 Importing events...")
        events_file = os.path.join(base_path , 'events_forecast.json')
        with open(events_file , encoding='utf-8') as f:
            data = json.load(f)
            for item in data['sample_data']:
                c.execute("""INSERT INTO events VALUES (?, ?, ?, ?)""" ,
                          (item['event_name'] , item['date'] ,
                           item['impact_level'] , item.get('event_name' , '')))
        print("  ✅ Events imported")

        conn.commit()
        print("\n✅ All data imported successfully!")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Could not find file")
        print(f"   {e}")
        print(f"\n💡 Make sure your JSON files are in:")
        print(f"   {base_path}")

    except Exception as e:
        print(f"\n❌ Error importing data: {e}")

    finally:
        conn.close()


if __name__ == '__main__':
    print("🔧 Setting up database...")
    create_database()
    import_json_data()
    print("\n✅ Database setup complete!")
    print("📁 Location: data/database.db")

    # اطبع عدد السجلات
    conn = sqlite3.connect('data/database.db')
    c = conn.cursor()

    print("\n📊 Database Statistics:")
    print(f"  - Inventory records: {c.execute('SELECT COUNT(*) FROM blood_inventory').fetchone()[0]}")
    print(f"  - Usage history records: {c.execute('SELECT COUNT(*) FROM blood_usage_history').fetchone()[0]}")
    print(f"  - Donors: {c.execute('SELECT COUNT(*) FROM donors').fetchone()[0]}")
    print(f"  - Inventory movements: {c.execute('SELECT COUNT(*) FROM inventory_movements').fetchone()[0]}")
    print(f"  - Events: {c.execute('SELECT COUNT(*) FROM events').fetchone()[0]}")

    conn.close()