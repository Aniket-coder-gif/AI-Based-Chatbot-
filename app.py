from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import google.generativeai as genai
import config
import requests
import uuid
from database import get_db
import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure Flask app
app.secret_key = config.SECRET_KEY
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=7)
app.config["SESSION_FILE_DIR"] = "./flask_session"
Session(app)

# Configure Google Gemini API
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
    logger.info("Google Gemini API configured successfully")
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")


@app.route('/')
def home():
    try:
        # Initialize a session if one doesn't exist
        if 'session_id' not in session:
            db = get_db()
            session['session_id'] = db.create_session()
            logger.info(f"Created new session: {session['session_id']}")
    except Exception as e:
        logger.error(f"Error creating session: {e}")

    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        # Get session ID or create one if it doesn't exist
        if 'session_id' not in session:
            db = get_db()
            session['session_id'] = db.create_session()
            logger.info(f"Created new session: {session['session_id']}")

        session_id = session['session_id']
        db = get_db()

        # Save the user message to the database
        db.save_message(session_id, user_message, "user")

        # Call the Gemini API
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Get chat history from the database
            chat_history = db.get_session_messages(session_id)

            # If there's previous chat history, include it in the context
            if chat_history:
                # Build a context string from the chat history
                context = "Previous conversation:\n"
                for msg in chat_history:
                    prefix = "User: " if msg["role"] == "user" else "Assistant: "
                    content = msg.get("content", "")
                    if content:
                        context += f"{prefix}{content}\n"

                # Add the context to the user message
                prompt = f"{context}\nUser: {user_message}\nAssistant:"
                response = model.generate_content(prompt)
            else:
                # No history, just send the user message
                response = model.generate_content(user_message)

            # Extract the response text
            bot_response = response.text

            # Save the bot response to the database
            db.save_message(session_id, bot_response, "assistant")

            # Update session activity
            db.update_session_activity(session_id)

            return jsonify({'response': bot_response})
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return jsonify({'error': f"AI service error: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        if 'session_id' not in session:
            return jsonify({'history': []})

        session_id = session['session_id']
        db = get_db()

        # Get chat history from the database
        chat_history = db.get_session_messages(session_id)

        # Convert MongoDB objects to JSON-compatible format
        formatted_history = []
        for msg in chat_history:
            try:
                # Handle both MongoDB ObjectId and string ID formats
                msg_id = str(msg.get('_id', ''))

                # Handle both datetime and string timestamp formats
                timestamp = msg.get('timestamp')
                if hasattr(timestamp, 'isoformat'):
                    timestamp = timestamp.isoformat()
                elif not isinstance(timestamp, str):
                    timestamp = datetime.datetime.now().isoformat()

                formatted_history.append({
                    'id': msg_id,
                    'content': msg.get('content', ''),
                    'role': msg.get('role', 'unknown'),
                    'timestamp': timestamp
                })
            except Exception as e:
                logger.error(f"Error formatting message: {e}")

        return jsonify({'history': formatted_history})

    except Exception as e:
        logger.error(f"History endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    try:
        # Create a new session to effectively clear history
        db = get_db()
        new_session_id = db.create_session()

        # Update session
        session['session_id'] = new_session_id
        logger.info(
            f"Created new session (clearing history): {new_session_id}")

        return jsonify({'success': True, 'message': 'Chat history cleared'})

    except Exception as e:
        logger.error(f"Clear history endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Health check endpoint to verify service status"""
    try:
        db = get_db()
        mongo_status = "offline"

        # Check if using fallback
        if hasattr(db, 'using_fallback'):
            mongo_status = "offline (using file fallback)" if db.using_fallback else "online"

        # Check Gemini API
        gemini_status = "unknown"
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Hello")
            gemini_status = "online"
        except Exception as e:
            gemini_status = f"offline ({str(e)})"

        return jsonify({
            'service': 'AI Chat Assistant',
            'status': 'operational',
            'mongodb': mongo_status,
            'gemini_api': gemini_status,
            'session_active': 'session_id' in session
        })
    except Exception as e:
        return jsonify({
            'service': 'AI Chat Assistant',
            'status': 'degraded',
            'error': str(e)
        }), 500


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    # Ensure session directory exists
    os.makedirs("./flask_session", exist_ok=True)

    # Ensure chat data directory exists
    os.makedirs("./chat_data", exist_ok=True)

    app.run(debug=True)
