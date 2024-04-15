from csv import reader
from datetime import datetime
from domain.accelerometer import Accelerometer
from domain.gps import Gps
from domain.parking import Parking
from domain.aggregated_data import AggregatedData
import config


class FileDatasource:
    def __init__(self, accelerometer_filename: str, gps_filename: str, parking_filename: str) -> None:
        self.accelerometer_filename = accelerometer_filename
        self.gps_filename = gps_filename
        self.parking_filename = parking_filename


    def read(self) -> AggregatedData:
        accelerometer_row = next(self.accelerometer_reader, None)
        gps_row = next(self.gps_reader, None)
        parking_row = next(self.parking_reader, None)

        if accelerometer_row is None:
            self.accelerometer_file.seek(0)
            next(self.accelerometer_reader)
            accelerometer_row = next(reader(self.accelerometer_file), None)

        if gps_row is None:
            self.gps_file.seek(0)
            next(self.gps_reader)
            gps_row = next(reader(self.gps_file), None)

        if parking_row is None:
            self.parking_file.seek(0)
            next(self.parking_reader)
            parking_row = next(reader(self.parking_file), None)

        accelerometer_data = [int(x) for x in accelerometer_row]
        gps_data = [float(x) for x in gps_row]
        parking_data = (int(parking_row[0]), Gps(*gps_data))

        return AggregatedData(
            Accelerometer(*accelerometer_data),
            Gps(*gps_data),
            Parking(*parking_data),
            datetime.now(),
            config.USER_ID,
        )

    def startReading(self, *args, **kwargs):
        self.accelerometer_file = open(self.accelerometer_filename, "r")
        self.accelerometer_reader = reader(open(self.accelerometer_filename, "r"))
        next(self.accelerometer_reader)

        self.gps_file = open(self.gps_filename, "r")
        self.gps_reader = reader(self.gps_file)
        next(self.gps_reader)

        self.parking_file = open(self.parking_filename, "r")
        self.parking_reader = reader(self.parking_file)
        next(self.parking_reader)


    def stopReading(self, *args, **kwargs):
        self.accelerometer_file.close()
        self.gps_file.close()
        self.parking_file.close()
