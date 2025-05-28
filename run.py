from app import create_app, db
from app.models.user import User

app = create_app()

# Only run user creation if this is the main script
if __name__ == '__main__':
    # Create an application context
    with app.app_context():
        # List of users to check/create
        users_to_create = [
            {"username": "sara", "password": "password123", "role": "HR"},
            {"username": "gmi1", "password": "password123", "role": "HR"},
            {"username": "gmi2", "password": "password123", "role": "HR"},
            {"username": "sav", "password": "password123", "role": "HR"},
            {"username": "DRH", "password": "password123", "role": "DG"}
        ]
        
        # Check and create users
        for user_data in users_to_create:
            username = user_data["username"]
            existing_user = User.query.filter_by(username=username).first()
            
            if existing_user:
                print(f"User '{username}' already exists with role '{existing_user.role}'")
                # Update role if different
                if existing_user.role != user_data["role"]:
                    existing_user.role = user_data["role"]
                    print(f"Updated {username}'s role to {user_data['role']}")
            else:
                # Create new user
                new_user = User(username=username, role=user_data["role"])
                new_user.set_password(user_data["password"])
                db.session.add(new_user)
                print(f"Created new user '{username}' with role '{user_data['role']}'")
        
        # Commit all changes
        db.session.commit()
        print("All users checked/created successfully!")
    
    # Run the application on all interfaces (0.0.0.0) and port 500
    app.run(host='0.0.0.0', port=5004, debug=True) 