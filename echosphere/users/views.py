# users/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm
class CustomLoginView(LoginView):
    """Custom login view with better styling"""
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('chat:room_list')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)
class RegisterView(CreateView):
    """User registration view"""
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')
    def form_valid(self, form):
        """Process valid registration form"""
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(
            self.request,
            f'Account created for {username}! You can now log in.'
        )
        return response
    def form_invalid(self, form):
        """Handle form errors"""
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field}: {error}')
        return super().form_invalid(form)
@login_required
def profile_view(request):
    """Display and update user profile"""
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, 
            instance=request.user.profile
        )
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('users:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'users/profile.html', context)
def register_view(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(
                request, 
                f'Account created for {username}! You can now log in.'
            )
            return redirect('users:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})