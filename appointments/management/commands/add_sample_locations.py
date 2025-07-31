from django.core.management.base import BaseCommand
from appointments.models import Organization
import random

class Command(BaseCommand):
    help = 'Add sample location data to organizations for testing maps'

    def handle(self, *args, **options):
        # Sample locations (latitude, longitude, name, address)
        sample_locations = [
            (40.7128, -74.0060, "Manhattan Medical Center", "123 Broadway, New York, NY 10001"),
            (40.7589, -73.9851, "Times Square Clinic", "456 7th Ave, New York, NY 10018"),
            (40.7505, -73.9934, "Chelsea Health Center", "789 6th Ave, New York, NY 10011"),
            (40.7829, -73.9654, "Upper East Side Hospital", "321 Park Ave, New York, NY 10022"),
            (40.7484, -73.9857, "Midtown Medical Group", "654 5th Ave, New York, NY 10019"),
            (40.7614, -73.9776, "Central Park Medical", "987 Madison Ave, New York, NY 10021"),
            (40.7549, -73.9840, "Rockefeller Medical", "555 5th Ave, New York, NY 10017"),
            (40.7587, -73.9787, "Bryant Park Clinic", "222 42nd St, New York, NY 10036"),
            (40.7505, -73.9934, "Herald Square Medical", "333 6th Ave, New York, NY 10011"),
            (40.7484, -73.9857, "Empire State Medical", "444 5th Ave, New York, NY 10018"),
        ]

        organizations = Organization.objects.all()
        
        if not organizations.exists():
            self.stdout.write(
                self.style.WARNING('No organizations found. Please run setup_system first.')
            )
            return

        updated_count = 0
        
        for i, org in enumerate(organizations):
            if i < len(sample_locations):
                lat, lng, name, address = sample_locations[i]
                
                # Add some randomization to make it more realistic
                lat += random.uniform(-0.01, 0.01)
                lng += random.uniform(-0.01, 0.01)
                
                org.latitude = lat
                org.longitude = lng
                org.address = address
                org.name = name
                org.save()
                
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {org.name} with location: {lat:.6f}, {lng:.6f}')
                )
            else:
                # For remaining organizations, use random locations around NYC
                lat = 40.7128 + random.uniform(-0.1, 0.1)
                lng = -74.0060 + random.uniform(-0.1, 0.1)
                
                org.latitude = lat
                org.longitude = lng
                org.address = f"Sample Address {org.id}, New York, NY"
                org.save()
                
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {org.name} with random location: {lat:.6f}, {lng:.6f}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} organizations with location data')
        )
        
        self.stdout.write(
            self.style.SUCCESS('You can now test the maps feature at /maps/')
        ) 