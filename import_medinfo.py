import csv
from app import db, MedInfo, app

with app.app_context():
    with open('medinfo.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            med = MedInfo(
                med_name=row['med_name'],
                brand=row['brand'],
                category=row['category'],
                type=row['type']
            )
            db.session.add(med)
        db.session.commit()
    print("Data imported successfully!")
    