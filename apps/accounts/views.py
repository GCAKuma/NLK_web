from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import AddressForm, ProfileForm, RegistrationForm


@login_required
def profile(request):
    """Account page: edit personal details and the saved delivery address."""
    address = getattr(request.user, "address", None)
    profile_form = ProfileForm(instance=request.user)
    address_form = AddressForm(instance=address)

    if request.method == "POST":
        if "save_profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your details have been updated.")
                return redirect("accounts:profile")
        elif "save_address" in request.POST:
            address_form = AddressForm(request.POST, instance=address)
            if address_form.is_valid():
                addr = address_form.save(commit=False)
                addr.user = request.user
                addr.save()
                messages.success(request, "Your delivery address has been saved.")
                return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile.html",
        {"profile_form": profile_form, "address_form": address_form},
    )


class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to NLK! Your account is ready.")
        return response
