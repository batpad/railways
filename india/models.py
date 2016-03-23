from __future__ import unicode_literals

from django.contrib.gis.db import models
import csv
import json
from django.contrib.gis.geos import Point
from geopy.distance import distance

class Station(models.Model):
    id = models.IntegerField(primary_key=True)
    data_id = models.IntegerField(db_index=True)
    code = models.CharField(max_length=16, db_index=True)
    name = models.CharField(max_length=255)
    zone = models.CharField(max_length=16)
    state = models.CharField(max_length=128)
    address = models.CharField(max_length=512, blank=True)
    point = models.PointField(blank=True, null=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return "%s: %s" % (self.code, self.name,)

    @classmethod
    def import_from_csv(kls, path_to_csv):
        stations = csv.DictReader(open(path_to_csv))
        for s in stations:
            station = Station(**s)
            station.save()
            print station.id

    @classmethod
    def import_locations(kls, path_to_json):
        geojson = json.load(open(path_to_json))
        features = geojson['features']
        for f in features:
            station_code = f['properties']['code'].upper()
            station = Station.objects.get(code=station_code)
            lon = f['geometry']['coordinates'][0]
            lat = f['geometry']['coordinates'][1]
            if lon == 0 or lon == '':
                continue
            try:
                pt = Point(lon, lat)
            except:
                print json.dumps(f)
                raise Error('bad lat-long')
            station.point = pt
            station.save()
            print station_code

    def get_geojson(self):
        return {
            'type': 'Feature',
            'geometry': json.loads(self.point.geojson) if self.point else None,
            'properties': {
                'code': self.code,
                'name': self.name,
                'state': self.state,
                'address': self.address
            }
        }

    def get_destinations(self):
        geojson = self.get_geojson()
        geojson['properties']['destinations'] = []
        for s in self.schedule_set.filter(minor_stop_number=0).select_related('train__to_station'):
            last_stop = s.train.to_station
            last_stop_geojson = last_stop.get_geojson()
            last_stop_geojson['properties']['train_number'] = s.train.number
            last_stop_geojson['properties']['train_name'] = s.train.name
            geojson['properties']['destinations'].append(last_stop_geojson)
        return geojson

    @classmethod
    def get_all_destinations(kls):
        return [s.get_destinations() for s in Station.objects.all()]

    @classmethod
    def import_osm_geojson(kls, path_to_file):
        osm_data = json.load(open(path_to_file))
        count = 0
        for feature in osm_data['features']:
            if 'ref' in feature['properties']:
                count += 1
                code = feature['properties']['ref']
                try:
                    station = Station.objects.get(code=code)
                except:
                    continue
                station.point = Point(feature['geometry']['coordinates'][0], feature['geometry']['coordinates'][1])
                station.save()
                print station.name
        print count

    @classmethod
    def match_osm_names(kls, path_to_file):
        osm_data = json.load(open(path_to_file))
        for feature in osm_data['features']:
            if 'name' in feature['properties']:
                name = feature['properties']['name']
                first_name = name.split(' ')[0]
                stations = Station.objects.filter(point=None).filter(name__iexact=first_name)
                if stations.count() == 1:
                    station = stations[0]
                    station.point = Point(feature['geometry']['coordinates'][0], feature['geometry']['coordinates'][1])
                    station.save()
                    print station.name


class Train(models.Model):
    id = models.IntegerField(primary_key=True)
    data_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=512)
    number = models.CharField(max_length=64, db_index=True)
    return_train = models.CharField(max_length=64, db_index=True, blank=True, null=True)
    duration_h = models.IntegerField()
    duration_m = models.IntegerField()
    zone = models.CharField(max_length=16, blank=True)
    date_from = models.CharField(max_length=32, blank=True)
    date_to = models.CharField(max_length=32, blank=True)
    from_station = models.ForeignKey("Station", related_name="trains_from")
    to_station = models.ForeignKey("Station", related_name="trains_to")
    number_of_halts = models.IntegerField(null=True)
    typ = models.CharField(max_length=16, blank=True)
    departure = models.TimeField(null=True, blank=True)
    arrival = models.TimeField(null=True, blank=True)
    distance = models.IntegerField()
    departure_days = models.CharField(max_length=16, blank=True)
    monday = models.BooleanField()
    tuesday = models.BooleanField()
    wednesday = models.BooleanField()
    thursday = models.BooleanField()
    friday = models.BooleanField()
    saturday = models.BooleanField()
    sunday = models.BooleanField()
    classes = models.CharField(max_length=32, blank=True)
    chair_car = models.BooleanField()
    sleeper = models.BooleanField()
    first_class = models.BooleanField()
    third_ac = models.BooleanField()
    second_ac = models.BooleanField()
    first_ac = models.BooleanField()

    def __unicode__(self):
        return "%s: %s" % (self.number, self.name)

    def get_line_geojson(self):
        schedules = self.schedule_set.filter(is_suspicious=False).select_related('station')
        line_coords = []
        for schedule in schedules:
            station = schedule.station
            if not station or not station.point:
                continue
            line_coords.append([station.point.x, station.point.y])
        properties = {
            'number': self.number,
            'name': self.name
        }
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': line_coords
            },
            'properties': properties
        }

    def set_schedule_distance(self):
        schedules = self.schedule_set.all().values('id', 'distance_travelled')
        first_sched = Schedule.objects.get(id=schedules[0]['id'])
        first_sched.distance_from_previous = 0
        first_sched.save()
        for i, schedule in enumerate(schedules, start=0):
            if i == 0:
                continue
            previous = schedules[i-1]
            if schedule['distance_travelled'] and previous['distance_travelled']:
                distance = schedule['distance_travelled'] - previous['distance_travelled']
            else:
                distance = 10 #UGLY!!!!!!

            sched = Schedule.objects.get(id=schedule['id'])
            sched.distance_from_previous = distance
            # print sched.id
            sched.save()

    def flag_suspicious_schedules(self):
        schedules = list(self.schedule_set.all().select_related('station'))
        previous_point = None
        previous_distance = 0
        suspicions = []
        for i, schedule in enumerate(schedules):
            if schedule.station.point:
                has_point = True
            else:
                has_point = False
            if not has_point:
                previous_distance = previous_distance + schedule.distance_from_previous
                continue
            else:
                if previous_point is None:
                    previous_distance += schedule.distance_from_previous
                    previous_point = schedule.station.point
                    continue
                expected_distance = previous_distance + schedule.distance_from_previous
                actual_distance = distance(previous_point, schedule.station.point).km
                distance_buffer = expected_distance
                if distance_buffer < 25:
                    distance_buffer = 25
                if actual_distance > expected_distance + distance_buffer:
                    schedule.is_suspicious = True
                    suspicion = {
                        'id': schedule.id,
                        'expected_distance': expected_distance,
                        'actual_distance': actual_distance
                    }
                    suspicions.append(suspicion)
                    print suspicion
                    schedule.save()
                previous_distance = 0
                previous_point = schedule.station.point
        # out = open("suspicious_schedules.json", "w")
        # out.write(json.dumps(suspicions))
        # out.close()




    def get_stations_geojson(self):
        schedules = self.schedule_set.filter(minor_stop_number=0).select_related('station')
        features = [s.get_geojson() for s in schedules if s.station.point is not None]
        return {
            'type': 'FeatureCollection',
            'features': features
        }

    @classmethod
    def import_from_csv(kls, path_to_csv):
        trains = csv.DictReader(open(path_to_csv))
        for t in trains:
            if t['return_train'] == '':
                t['return_train'] = None
            train = Train(**t)
            train.save()
            print train.name


    @classmethod
    def get_featurecollection(kls, path_to_file):
        return {
            'type': 'FeatureCollection',
            'features': [t.get_line_geojson() for t in Train.objects.all()]
        }


class Schedule(models.Model):
    id = models.IntegerField(primary_key=True)
    arrival = models.TimeField(blank=True, null=True)
    departure = models.TimeField(blank=True, null=True)
    halt = models.IntegerField(blank=True, null=True)
    stop_number = models.IntegerField()
    minor_stop_number = models.IntegerField()
    station = models.ForeignKey(Station, blank=True, null=True)
    train = models.ForeignKey(Train, blank=True, null=True)
    day = models.IntegerField()
    distance_from_previous = models.IntegerField(null=True, blank=True)
    distance_travelled = models.IntegerField(blank=True, null=True)
    is_suspicious = models.BooleanField(default=False)

    class Meta:
        ordering = ['stop_number', 'minor_stop_number']

    def __unicode__(self):
        return str(self.id)

    def get_geojson(self):
        if not self.station.point:
            return None
        station_geojson = self.station.get_geojson()
        station_geojson['properties']['stop_number'] = self.stop_number
        station_geojson['properties']['minor_stop_number'] = self.minor_stop_number
        station_geojson['properties']['day'] = self.day
        station_geojson['properties']['time'] = self.get_time()
        return station_geojson

    def get_time(self):
        if self.arrival:
            return str(self.arrival)
        else:
            return str(self.departure)

    @classmethod
    def import_from_json(kls, path_to_json):
        station_errors = []
        train_errors = []
        schedules = json.load(open(path_to_json))
        for s in schedules:
            stop_number_split = s['stop_number'].split('.')
            stop_number = stop_number_split[0]
            if len(stop_number_split) > 1:
                minor_stop_number = stop_number_split[1]
            else:
                minor_stop_number = 0
            s['stop_number'] = stop_number
            s['minor_stop_number'] = minor_stop_number
            if s['arrival'] == '':
                s['arrival'] = None
            if s['departure'] == '':
                s['departure'] = None
            if s['halt'] == '':
                s['halt'] = None
            if s['halt']:
                s['halt'] = ''.join([d for d in s['halt'] if d.isdigit()])
            
            try:
                s['station'] = Station.objects.get(code=s['station_code'])
            except:
                s['station'] = None
                station_errors.append(s)

            try:
                s['train'] = Train.objects.get(number=s['train_number'])
            except:
                s['train'] = None
                train_errors.append(s)

            s.pop('station_code')
            s.pop('station_name')
            s.pop('train_number')
            schedule = Schedule(**s)
            schedule.save()
            print unicode(schedule) 
        station_errors_file = open('station_errors.json', "w")
        station_errors_file.write(json.dumps(station_errors))
        train_errors_file = open('train_errors.json', "w")
        train_errors_file.write(json.dumps(train_error))
        station_errors_file.close()
        train_errors_file.close()
        print "done"

    


