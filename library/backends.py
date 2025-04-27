from django_auth_adfs.backend import AdfsAuthCodeBackend

class CustomAdfsBackend(AdfsAuthCodeBackend):
    def create_user(self, claims):
        user = super().create_user(claims)
        
        # Set the user role based on group membership
        if 'groups' in claims:
            if 'Students' in claims['groups']:
                user.role = 'student'
            elif 'Teachers' in claims['groups']:
                user.role = 'teacher'
            elif 'Administrators' in claims['groups']:
                user.role = 'admin'
            user.save()
        
        return user

    def update_user(self, user, claims):
        user = super().update_user(user, claims)

        if 'groups' in claims:
            if 'Students' in claims['groups']:
                user.role = 'student'
            elif 'Teachers' in claims['groups']:
                user.role = 'teacher'
            elif 'Administrators' in claims['groups']:
                user.role = 'admin'
            user.save()
            
        return user