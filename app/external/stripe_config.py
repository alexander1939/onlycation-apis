import stripe
from app.configs.settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeConfig:
    def __init__(self):
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.public_key = settings.STRIPE_PUBLIC_KEY

    def init(self):
        stripe.api_key = self.secret_key

stripe_config = StripeConfig()
stripe_config.init()