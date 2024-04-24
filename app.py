from flask import Flask, render_template

# Initialize Flask app
app = Flask(__name__)

# Route for the main page
@app.route('/')
def index():
  # Example data to pass to the template
  data = {'title': 'My Flask App', 'message': 'Welcome!'}
  return render_template('index.html', data=data)  # Render index.html with data

# Run the application in debug mode (for development)
if __name__ == '__main__':
  app.run(debug=True)
