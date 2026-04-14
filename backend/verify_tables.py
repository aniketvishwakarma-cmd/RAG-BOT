from app.db.session import engine
from sqlalchemy import text

def verify_tables():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]
        print("Tables created in Supabase:")
        for table in sorted(tables):
            print(f"  - {table}")
        
        # Check if our main tables exist
        expected_tables = ['documents', 'chunks', 'queries', 'citations', 'audit_logs', 'graph_relations']
        missing = [t for t in expected_tables if t not in tables]
        if missing:
            print(f"\nMissing tables: {missing}")
        else:
            print(f"\n✅ All expected tables created successfully!")

if __name__ == "__main__":
    verify_tables()
