from django.shortcuts import render, redirect
from .forms import UserForm, StatementForm, EditProfileForm,PasswordChangeForm,OTPForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from datetime import datetime
from django.contrib.auth import authenticate, login, update_session_auth_hash
import traceback
from django.contrib import messages 
from .utils import generate_otp, send_otp_email ,check_otp
from .models import Statement, CustomUser, Form, Verdict
import re
from bs4 import BeautifulSoup
import keras
from keras.models import load_model  
import tensorflow as tf
from keras.preprocessing.sequence import pad_sequences
from django_tables2 import RequestConfig
from .tables import StatementVerdictTable
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from django.utils import timezone
# Your Django view function here


# Create your views here.
def home(request):
    return render(request, 'users/home.html')

def register(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Hi {username}, your account was created successfully')
            return redirect('login')
    else:
        form = UserForm()
    return render(request, 'users/register.html', {'form': form})

@login_required()
def user_profile(request):
    return render(request, 'users/profile.html')



def login_view(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            password = request.POST['password']

            # Authenticate the user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Store the username and last_activity timestamp in the session
                request.session['username'] = username
                request.session['last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

                # Generate an OTP
                otp = generate_otp()

                # Send the OTP to the user's email
                send_otp_email(user.email, otp)  # Replace 'user.email' with the actual user email field

                # Store the OTP in the session
                request.session['otp'] = otp

                # Log in the user
                login(request, user)

                # Redirect to the OTP verification page
                return redirect('verify_otp')
        except Exception as e:
            # Handle exceptions here, e.g., log the exception
            traceback.print_exc()

    # Handle GET requests (display login form)
    return render(request, 'users/login.html')



    

def logout_view(request):
    # Log the user out
    logout(request)

    
    return redirect('logout')  




# Your preprocessing functions
def strip_html(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()

def remove_text_before_sentences(text):
    text = re.sub(r'^[A-Z]+\s*-\s*', '', text)
    return text

def remove_words_in_parentheses(text):
    return re.sub(r'\([^)]*\)', '', text)

def remove_dashes(text):
    return text.replace('-', '')

def remove_symbols(text):
    pattern = r'[^A-Za-z0-9\s]'
    return re.sub(pattern, '', text)

def denoise_text(text):
    text = strip_html(text)
    text = remove_text_before_sentences(text)
    text = remove_words_in_parentheses(text)
    text = remove_dashes(text)
    text = remove_symbols(text)
    return text

# Tokenizer settings
max_features = 20000
maxlen = 300
tokenizer = tf.keras.preprocessing.text.Tokenizer(num_words=max_features)




@login_required
def statement(request):
    verdict = None
    probability_percentage = None

    if request.method == "POST":
        form = StatementForm(request.POST)
        if form.is_valid():
            statement_text = form.cleaned_data['statement']
            cleaned_statement = denoise_text(statement_text)

            # Tokenize and pad the input
            tokenizer.fit_on_texts([cleaned_statement])
            sequences = tokenizer.texts_to_sequences([cleaned_statement])
            input_data = pad_sequences(sequences, maxlen=maxlen)

            # Load your pre-trained model 
            model = load_model('/Users/nyagaderrick/Developer/136788/Credibility_verification_system/models/cvs_model.h5')

            # Make a prediction using loaded model
            predicted_probability = model.predict(input_data)
            threshold = 0.5 # Adjust the threshold as needed
            predicted_label = "True" if predicted_probability >= threshold else "False"

            # Save the cleaned statement to  database
            statement_obj = Statement(
                user_id=request.user,
                statement=cleaned_statement
            )
            statement_obj.save()

            # Create a Form entry for the current user and statement
            form_obj = Form(
                user_id=request.user,
                statement_id=statement_obj
            )
            form_obj.save()

            # Create a Verdict entry with the form and statement references
            verdict_label = "True" if predicted_label == "True" else "False"
            verdict_obj = Verdict(
                form_id=form_obj,
                statement_id=statement_obj,
                Statement_verdict=verdict_label,
                predicted_probability=predicted_probability[0][0] * 100  # Convert to percentage
            )
            verdict_obj.save()

            verdict = verdict_label
            probability_percentage = predicted_probability[0][0] * 100

    else:
        form = StatementForm()

    return render(request, 'users/statement.html', {'form': form, 'verdict': verdict, 'probability_percentage': probability_percentage})





@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()

            # Add a success message
            messages.success(request, 'Your credentials have been changed successfully.')

            return redirect('statement')  # Redirect to the user's profile page
    else:
        form = EditProfileForm(instance=request.user)

    return render(request, 'users/edit_profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important for keeping the user logged in
            return redirect('edit_profile')  # Redirect to the user's profile page after password change
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/password.html', {'form': form})



@login_required
def verify_otp(request):
    error_message = None  # Initialize error message as None
    success_message = None  # Initialize success message as None

    if request.method == 'POST':
        # Get the entered OTP from the form
        form = OTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']

            # Check the entered OTP using the check_otp function
            otp_status = check_otp(request, entered_otp)
            if otp_status == 'valid':
                # OTP is valid and not expired, allow the user to access statements
                del request.session['otp']  # Remove OTP from the user's session
                del request.session['otp_time']  # Remove OTP time from the user's session
                return redirect('statement')  # Redirect to the statements view
            elif otp_status == 'expired':
                # OTP is expired, log the user out and redirect to login page
                logout(request)
                return redirect('login')
            else:
                # OTP is invalid, set the error_message
                error_message = 'The OTP you entered is incorrect. Please check your email for the latest OTP.'
    else:
        # Generate and send a new OTP when the page is initially loaded
        otp = generate_otp(request)
        send_otp_email(request.user.email, otp)  # Replace 'request.user.email' with the actual user email field
        request.session['otp'] = otp  # Store the OTP in the user's session
        request.session['otp_time'] = str(timezone.now())

        # Set the success_message for OTP sent
        success_message = f'Success! An OTP code has been sent to your Email {hide_email(request.user.email)}.'

    # Display OTP verification form
    form = OTPForm()

    # Handle the "Back to login" action
    if 'back_to_login' in request.POST:
        logout(request)  # Log the user out
        return redirect('login')  # Redirect to the login page

    return render(request, 'users/verify_otp.html', {'form': form, 'error_message': error_message, 'success_message': success_message})


def hide_email(email):
    # Helper function to hide part of the email address
    parts = email.split('@')
    return f'{parts[0][:3]}***@{parts[1]}'  # Display part of the email





@login_required
def user_dashboard(request):
    user = request.user

    # Fetch statements and verdicts specific to the user and select specific columns
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    verdict_true = request.GET.get('verdict_true')
    verdict_false = request.GET.get('verdict_false')

    try:
        statements = Statement.objects.filter(user_id=user).values('id', 'statement', 'created_at')
        verdicts = Verdict.objects.filter(statement_id__user_id=user).values('Statement_verdict', 'predicted_probability')

        # Apply date filter
        if start_date and end_date:
            start_date = make_aware(datetime.datetime.strptime(start_date, '%Y-%m-%d'))
            end_date = make_aware(datetime.datetime.strptime(end_date, '%Y-%m-%d'))
            statements = statements.filter(created_at__range=(start_date, end_date))
            verdicts = verdicts.filter(statement_id__created_at__range=(start_date, end_date))

        # Apply verdict filter
        if verdict_true:
            verdicts = verdicts.filter(Statement_verdict=True)

        if verdict_false:
            verdicts = verdicts.filter(Statement_verdict=False)

        # Combine data from statements and verdicts
        data = []
        for statement, verdict in zip(statements, verdicts):
            data.append({
                'statement_id': statement['id'],
                'truncated_statement': statement['statement'][:50] + '...' if len(statement['statement']) > 50 else statement['statement'],
                'created_at': statement['created_at'],
                'Statement_verdict': verdict['Statement_verdict'],
                'predicted_probability': verdict['predicted_probability'],
            })

        context = {
            'data': data,
            'start_date': start_date,
            'end_date': end_date,
            'verdict_true': verdict_true,
            'verdict_false': verdict_false,
        }
        return render(request, 'users/user_dashboard.html', context)

    except Exception as e:
        print(f"An error occurred: {e}")
        raise  # Re-raise the exception to see the full traceback in the console


# def tables(request):
#     return render(request, 'users/tables.html')