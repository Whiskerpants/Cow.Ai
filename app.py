from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///herdcycle.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@herdcycle.com')

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)


# Database Models
class PilotApplication(db.Model):
    __tablename__ = 'pilot_applications'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    ranch_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    herd_size = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    biggest_challenge = db.Column(db.String(100), nullable=False)
    test_cows = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    review_queue = db.relationship('ReviewQueue', backref='application', uselist=False)
    logs = db.relationship('ApplicationLog', backref='application')


class ReviewQueue(db.Model):
    __tablename__ = 'review_queue'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('pilot_applications.id'))
    priority = db.Column(db.String(20), default='normal')
    assigned_to = db.Column(db.String(255))
    status = db.Column(db.String(50), default='awaiting_review')
    notes = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)


class ApplicationLog(db.Model):
    __tablename__ = 'application_logs'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('pilot_applications.id'))
    event_type = db.Column(db.String(100))
    event_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Helper functions
def determine_priority(herd_size):
    """Determine application priority based on herd size"""
    if herd_size in ['1000+', '500-1000']:
        return 'high'
    elif herd_size in ['250-500']:
        return 'medium'
    return 'normal'


def send_confirmation_email(application):
    """Send confirmation email to applicant"""
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #059669;">Thank you for applying, {application.name}!</h2>

        <p>We've received your application for the HerdCycle Smart Tags pilot program.</p>

        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">Application Details:</h3>
            <p><strong>Ranch:</strong> {application.ranch_name}</p>
            <p><strong>Location:</strong> {application.location}</p>
            <p><strong>Herd Size:</strong> {application.herd_size}</p>
            <p><strong>Application ID:</strong> #{application.id}</p>
        </div>

        <h3>What happens next?</h3>
        <ol>
            <li>Our team will review your application within 48 hours</li>
            <li>If selected, you'll receive shipping details for your 5 free smart tags</li>
            <li>We'll provide setup instructions and access to our monitoring dashboard</li>
        </ol>

       <p>If you have any questions, reply to this email or contact us at herdcycle.com.</p>
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            This is an automated email. Your application was submitted on {application.created_at.strftime('%B %d, %Y at %I:%M %p')}.
        </p>
    </div>
    """

    msg = Message(
        subject='Application Received - HerdCycle Pilot Program',
        recipients=[application.email],
        html=html_body
    )

    mail.send(msg)


def send_team_notification(application, priority):
    """Send notification to internal team"""
    admin_url = os.getenv('ADMIN_URL', 'https://admin.ranchtech.com')
    team_email = os.getenv('TEAM_EMAIL', 'team@ranchtech.com')

    html_body = f"""
    <h3>New Application Received</h3>
    <p><strong>Priority:</strong> {priority.upper()}</p>
    <p><strong>Name:</strong> {application.name}</p>
    <p><strong>Ranch:</strong> {application.ranch_name}</p>
    <p><strong>Location:</strong> {application.location}</p>
    <p><strong>Herd Size:</strong> {application.herd_size}</p>
    <p><strong>Challenge:</strong> {application.biggest_challenge}</p>
    <p><strong>Test Plans:</strong> {application.test_cows or 'Not specified'}</p>
    <p><a href="{admin_url}/applications/{application.id}">Review Application</a></p>
    """

    msg = Message(
        subject=f'New Pilot Application - {application.ranch_name} ({application.herd_size})',
        recipients=[team_email],
        html=html_body
    )

    mail.send(msg)


# Routes
@app.route('/signup', methods=['POST'])
def signup():
    """Handle pilot program signup form submission"""
    try:
        # Get form data
        data = request.form

        # Validate required fields
        required_fields = ['name', 'ranch', 'email', 'phone', 'herd_size', 'location', 'biggest_challenge']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Check for existing application
        existing = PilotApplication.query.filter_by(email=data['email']).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'An application with this email already exists'
            }), 400

        # Create new application
        application = PilotApplication(
            name=data['name'],
            ranch_name=data['ranch'],
            email=data['email'],
            phone=data['phone'],
            herd_size=data['herd_size'],
            location=data['location'],
            biggest_challenge=data['biggest_challenge'],
            test_cows=data.get('test_cows', '')
        )

        db.session.add(application)
        db.session.flush()  # Get the ID without committing

        # Add to review queue
        priority = determine_priority(data['herd_size'])
        review_queue = ReviewQueue(
            application_id=application.id,
            priority=priority
        )
        db.session.add(review_queue)

        # Log the application
        log_entry = ApplicationLog(
            application_id=application.id,
            event_type='application_submitted',
            event_data={
                'source': 'web_form',
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }
        )
        db.session.add(log_entry)

        # Commit all changes
        db.session.commit()

        # Send emails (after successful commit)
        try:
            send_confirmation_email(application)
            send_team_notification(application, priority)
        except Exception as email_error:
            # Log email error but don't fail the request
            print(f"Email error: {email_error}")
            # You might want to add this to a retry queue

        # Return success response
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully',
            'applicationId': application.id
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Signup error: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your application. Please try again.'
        }), 500


@app.route('/api/application/<int:app_id>', methods=['GET'])
def get_application(app_id):
    """Get application details (for admin interface)"""
    application = PilotApplication.query.get_or_404(app_id)

    return jsonify({
        'id': application.id,
        'name': application.name,
        'ranch_name': application.ranch_name,
        'email': application.email,
        'phone': application.phone,
        'herd_size': application.herd_size,
        'location': application.location,
        'biggest_challenge': application.biggest_challenge,
        'test_cows': application.test_cows,
        'status': application.status,
        'created_at': application.created_at.isoformat(),
        'review_queue': {
            'priority': application.review_queue.priority,
            'status': application.review_queue.status,
            'assigned_to': application.review_queue.assigned_to
        } if application.review_queue else None
    })


@app.route('/api/queue/pending', methods=['GET'])
def get_pending_applications():
    """Get all pending applications in the review queue"""
    pending = db.session.query(PilotApplication, ReviewQueue) \
        .join(ReviewQueue) \
        .filter(ReviewQueue.status == 'awaiting_review') \
        .order_by(
        db.case(
            (ReviewQueue.priority == 'high', 1),
            (ReviewQueue.priority == 'medium', 2),
            (ReviewQueue.priority == 'normal', 3)
        ),
        PilotApplication.created_at
    ).all()

    results = []
    for app, queue in pending:
        results.append({
            'id': app.id,
            'name': app.name,
            'ranch_name': app.ranch_name,
            'location': app.location,
            'herd_size': app.herd_size,
            'priority': queue.priority,
            'created_at': app.created_at.isoformat()
        })

    return jsonify(results)


# Database initialization
def create_tables():
    """Create database tables if they don't exist"""
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
        return render_template('index.html')


# Create tables when running directly
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)


# Environment variables template
"""
# Create a .env file with these variables:

# Database
DATABASE_URL=postgresql://username:password@localhost/ranchtech_db

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@ranchtech.com

# Application Settings
TEAM_EMAIL=team@ranchtech.com
ADMIN_URL=https://admin.ranchtech.com
"""




