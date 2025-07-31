from channels.testing import ChannelsLiveServerTestCase

class MinimalChannelsTest(ChannelsLiveServerTestCase):
    def test_dummy(self):
        self.assertTrue(True) 