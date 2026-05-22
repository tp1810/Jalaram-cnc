from django.utils import timezone


def site_info(request):
    return {
        'today': timezone.now().date(),
        'business_name': 'Jalaram CNC Art & Craft',
    }
