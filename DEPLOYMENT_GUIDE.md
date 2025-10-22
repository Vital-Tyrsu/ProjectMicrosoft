# 🚀 PythonAnywhere Deployment Guide

## Step 1: Sign Up for PythonAnywhere
1. Go to https://www.pythonanywhere.com/
2. Click "Pricing & signup"
3. Choose **"Create a Beginner account"** (FREE)
4. Verify your email

---

## Step 2: Upload Your Code

### Option A: Using Git (Recommended)
1. Push your code to GitHub first:
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. On PythonAnywhere, open a **Bash console**
3. Clone your repository:
   ```bash
   git clone https://github.com/Vital-Tyrsu/ProjectMicrosoft.git
   cd ProjectMicrosoft
   ```

### Option B: Upload Files Manually
1. Go to **Files** tab
2. Upload your project folder as a zip
3. Unzip it in the console

---

## Step 3: Set Up Virtual Environment

In the Bash console:
```bash
cd ProjectMicrosoft
mkvirtualenv --python=/usr/bin/python3.10 library-env
pip install -r requirements.txt
```

---

## Step 4: Configure Environment Variables

1. Go to **Web** tab
2. Scroll to **"Environment variables"** section
3. Add these variables:

```
SECRET_KEY = (generate new one at https://djecrety.ir/)
DEBUG = False
ALLOWED_HOSTS = yourusername.pythonanywhere.com
EMAIL_HOST_USER = vital.tyrsu@gmail.com
EMAIL_HOST_PASSWORD = (your Gmail app password)
SOCIAL_AUTH_GOOGLE_CLIENT_ID = (your Google OAuth client ID)
SOCIAL_AUTH_GOOGLE_CLIENT_SECRET = (your Google OAuth client secret)
```

---

## Step 5: Update Google OAuth Redirect URIs

1. Go to https://console.cloud.google.com/apis/credentials
2. Click on your OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs**:
   ```
   https://yourusername.pythonanywhere.com/accounts/google/login/callback/
   ```
4. Save changes

---

## Step 6: Set Up Django on PythonAnywhere

1. Go to **Web** tab
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"**
4. Select **Python 3.10**

### Configure WSGI file:
Click on **WSGI configuration file** link and replace content with:

```python
import os
import sys

# Add your project directory to the sys.path
project_home = '/home/yourusername/ProjectMicrosoft'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'library_system.settings'

# Load .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Activate virtual environment
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Configure Virtual Environment:
1. Scroll to **"Virtualenv"** section
2. Enter: `/home/yourusername/.virtualenvs/library-env`

### Configure Static Files:
1. Scroll to **"Static files"** section
2. Add:
   - URL: `/static/`
   - Directory: `/home/yourusername/ProjectMicrosoft/static`
3. Add:
   - URL: `/media/`
   - Directory: `/home/yourusername/ProjectMicrosoft/media`

---

## Step 7: Run Django Commands

In the Bash console:
```bash
cd ProjectMicrosoft
workon library-env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## Step 8: Create .env File on Server

In the Bash console:
```bash
cd ProjectMicrosoft
nano .env
```

Paste your environment variables, then press `Ctrl+X`, `Y`, `Enter` to save.

---

## Step 9: Reload Your Web App

1. Go back to **Web** tab
2. Click the big green **"Reload"** button
3. Click on your app URL: `https://yourusername.pythonanywhere.com`

---

## ✅ Your App Should Now Be Live!

### Test the following:
- [ ] Can access the website
- [ ] Google Sign-In works
- [ ] Can create reservations
- [ ] Emails are being sent
- [ ] Admin panel works

---

## 🐛 Troubleshooting

### View Error Logs:
Go to **Web** tab → Click **"Error log"** or **"Server log"**

### Common Issues:

1. **500 Error** - Check error log for details
2. **Static files not loading** - Run `collectstatic` again
3. **Database errors** - Run `migrate` again
4. **Import errors** - Make sure all packages in requirements.txt

---

## 📧 Email Reminders Setup

To run daily email reminders, go to **Tasks** tab:
- Command: `cd /home/yourusername/ProjectMicrosoft && /home/yourusername/.virtualenvs/library-env/bin/python manage.py send_due_reminders`
- Time: `09:00` (daily)

---

## 🎉 You're Done!

Share your beta URL with testers: `https://yourusername.pythonanywhere.com`

Remember to:
- Monitor error logs during beta
- Collect user feedback
- Check email delivery

Good luck with your beta launch! 🚀
