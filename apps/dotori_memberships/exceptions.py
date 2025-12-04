
class FeatureLimitExceeded(Exception):
    """해당 기능의 일일 사용 한도를 초과했을 때 발생"""

    def __init__(self, feature_type: str, remaining: int = 0):
        self.feature_type = feature_type
        self.remaining = remaining
        msg = f"Feature {feature_type} limit exceeded (remaining={remaining})"
        super().__init__(msg)


class NotEnoughPoint(Exception):
    """포인트 부족"""

    def __init__(self, needed: int, current: int):
        self.needed = needed
        self.current = current
        msg = f"Not enough points: need {needed}, current {current}"
        super().__init__(msg)
