"""Quick demo data creation for testing controller APIs"""

import os
import sys
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from models import Train, Conflict, Section, TrainType, ConflictSeverity
from db import get_engine

def create_demo_data():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if data already exists
        train_count = session.query(Train).count()
        if train_count > 0:
            print(f"✅ Already have {train_count} trains in database")
            conflict_count = session.query(Conflict).count()
            print(f"✅ Already have {conflict_count} conflicts in database")
            return
        
        print("Creating demo data...")
        
        # Create sections if they don't exist
        for i in range(1, 6):
            section = session.query(Section).filter_by(id=i).first()
            if not section:
                section = Section(
                    id=i,
                    name=f'Section {i}',
                    section_code=f'SEC{i:03d}',
                    section_type='track',
                    length_meters=50000.0,
                    max_speed_kmh=120,
                    capacity=2,
                    active=True
                )
                session.add(section)
        session.commit()
        
        # Create demo trains
        trains_data = [
            {'id': 1, 'train_no': 'TR001', 'type': TrainType.EXPRESS, 'section': 1, 'priority': 5},
            {'id': 2, 'train_no': 'TR002', 'type': TrainType.FREIGHT, 'section': 2, 'priority': 3},
            {'id': 3, 'train_no': 'TR003', 'type': TrainType.EXPRESS, 'section': 3, 'priority': 8},
            {'id': 4, 'train_no': 'TR004', 'type': TrainType.LOCAL, 'section': 4, 'priority': 4},
            {'id': 5, 'train_no': 'TR005', 'type': TrainType.LOCAL, 'section': 5, 'priority': 6},
        ]
        
        now = datetime.now(timezone.utc)
        for data in trains_data:
            train = Train(
                id=data['id'],
                train_no=data['train_no'],
                train_type=data['type'],
                origin='Station A',
                destination='Station F',
                scheduled_departure=now - timedelta(hours=1),
                scheduled_arrival=now + timedelta(hours=2),
                current_section_id=data['section'],
                status='running',
                priority=data['priority'],
                current_speed_kmh=80.0,
                delays_minutes=0
            )
            session.add(train)
        session.commit()
        print(f"✅ Created {len(trains_data)} demo trains")
        
        # Create demo conflicts
        conflicts_data = [
            {
                'id': 1,
                'conflict_type': 'scheduling',
                'severity': ConflictSeverity.HIGH,
                'trains_involved': [1, 2],
                'sections_involved': [1, 2],
                'description': 'Potential collision between TR001 and TR002 on Section 1',
                'estimated_impact_minutes': 15,
                'ai_recommendations': [
                    {
                        'action': 'delay_train',
                        'train_id': 2,
                        'delay_minutes': 10,
                        'rationale': 'Allow TR001 to clear section first',
                        'confidence': 0.89
                    }
                ]
            },
            {
                'id': 2,
                'conflict_type': 'resource',
                'severity': ConflictSeverity.MEDIUM,
                'trains_involved': [3, 4],
                'sections_involved': [3, 4],
                'description': 'Track capacity conflict between TR003 and TR004',
                'estimated_impact_minutes': 10,
                'ai_recommendations': [
                    {
                        'action': 'modify_speed',
                        'train_id': 4,
                        'new_speed': 60,
                        'rationale': 'Maintain safe spacing',
                        'confidence': 0.75
                    }
                ]
            },
            {
                'id': 3,
                'conflict_type': 'timing',
                'severity': ConflictSeverity.LOW,
                'trains_involved': [2, 5],
                'sections_involved': [2, 5],
                'description': 'Minor timing conflict for station platform access',
                'estimated_impact_minutes': 5,
                'ai_recommendations': [
                    {
                        'action': 'adjust_priority',
                        'train_id': 5,
                        'new_priority': 7,
                        'rationale': 'Passenger train should have priority',
                        'confidence': 0.92
                    }
                ]
            },
        ]
        
        for data in conflicts_data:
            conflict = Conflict(
                id=data['id'],
                conflict_type=data['conflict_type'],
                severity=data['severity'],
                trains_involved=data['trains_involved'],
                sections_involved=data['sections_involved'],
                detection_time=now - timedelta(minutes=5),
                description=data['description'],
                estimated_impact_minutes=data['estimated_impact_minutes'],
                auto_resolved=False,
                ai_analyzed=True,
                ai_confidence=0.85,
                ai_recommendations=json.dumps(data['ai_recommendations'])
            )
            session.add(conflict)
        session.commit()
        print(f"✅ Created {len(conflicts_data)} demo conflicts")
        
        print("\n✅ Demo data creation complete!")
        print("\nAvailable trains:")
        for t in trains_data:
            print(f"  - Train {t['id']} ({t['train_no']}): {t['type'].value} on Section {t['section']}")
        print("\nActive conflicts:")
        for c in conflicts_data:
            print(f"  - Conflict {c['id']}: {c['severity'].value} {c['conflict_type']} - {c['description'][:50]}...")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_demo_data()
