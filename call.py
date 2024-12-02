from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure the generative AI
google_api_key = os.getenv("GOOGLE_API_KEY")

# Twilio credentials (Make sure these are stored securely in environment variables)
account_sid = "your-account-sid"
auth_token = "auth-token"
twilio_number = "+replace-your-number"  # Replace with your Twilio phone number
client = Client(account_sid, auth_token)

# Function to generate a response using Generative AI
def generate_response(input_text):
    # Use Google Generative AI to create a response based on the user's input
    model = genai.GenerativeModel('gemini-1.5-flash')
    rply = model.generate_content(f"{input_text} your acting as a customer support team so answer to the given question in less than 3 lines")
    response = rply.text
    return response

# Route to handle incoming calls and gather voice input
@app.route('/incoming-call', methods=['GET', 'POST'])
def incoming_call():
    response = VoiceResponse()
    response.say("Hello! I'm your AI assistant.")
    
    # Gather voice input from the caller
    gather = Gather(input_='speech', action='/process-voice', language='en-GB', speech_model='phone_call',
                    hints='maneater, you make my dreams, out of touch, customer support, amazon')
    gather.say('Please ask your question after the beep.')
    response.append(gather)
    
    # If the caller doesn't say anything, prompt again
    response.redirect('/incoming-call')
    
    return str(response)

# Route to process the speech input
@app.route('/process-voice', methods=['POST'])
def process_voice():
    speech_result = request.values.get('SpeechResult')
    
    if speech_result:
        # Save the transcription for debugging purposes
        with open('transcription.txt', 'w') as f:
            f.write(speech_result)
        
        print("User said:", speech_result)
        
        # Check if the user says something like "Goodbye" to end the call
        if 'goodbye' in speech_result.lower() or 'bye' in speech_result.lower():
            response = VoiceResponse()
            response.say("Goodbye! Have a great day.")
            response.hangup()
            return str(response)

        # Generate a response using Google Generative AI based on the speech input
        generated_response = generate_response(speech_result)
        print("AI response:", generated_response)
        
        # Respond back to the caller with the generated response
        response = VoiceResponse()
        response.say(generated_response)
        
        # Prompt for another question after responding
        gather = Gather(input_='speech', action='/process-voice', language='en-GB', speech_model='phone_call',
                        hints='maneater, you make my dreams, out of touch, customer support, amazon')
        gather.say("You can ask another question, or say 'Goodbye' to end the call.")
        response.append(gather)

        return str(response)

    else:
        # If no speech was detected, prompt the user to try again
        response = VoiceResponse()
        response.say("Sorry, I didn't catch that. Could you please repeat?")
        response.redirect('/incoming-call')
        return str(response)

# Route to initiate an outbound call
@app.route('/make-call', methods=['POST'])
def make_call():
    to_number = request.json.get('to')  # JSON body should include the recipient's phone number
    
    call = client.calls.create(
        to=to_number,
        from_=twilio_number,
        url=' https://Your-website/incoming-call'  # Publicly accessible URL
    )
    
    return jsonify({"status": "Call initiated", "call_sid": call.sid})

# Function to initiate an outbound call via command line or API
def initiate_outbound_call(to_number):
    call = client.calls.create(
        to=to_number,
        from_=twilio_number,
        url=' https://your-website/incoming-call'  # Publicly accessible URL
    )
    return call.sid

if __name__ == "__main__":
    app.run(debug=True)