import logging
from typing import Tuple, List, Set

from custom_components.xiaomi_cloud_map_extractor.common.map_data import *
from custom_components.xiaomi_cloud_map_extractor.common.map_data_parser import MapDataParser
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, Sizes, Texts
from custom_components.xiaomi_cloud_map_extractor.xiaomi.image_handler import ImageHandlerXiaomi

_LOGGER = logging.getLogger(__name__)


class MapDataParserXiaomi(MapDataParser):
    CHARGER = 1
    IMAGE = 2
    PATH = 3
    GOTO_PATH = 4
    GOTO_PREDICTED_PATH = 5
    CURRENTLY_CLEANED_ZONES = 6
    GOTO_TARGET = 7
    ROBOT_POSITION = 8
    NO_GO_AREAS = 9
    VIRTUAL_WALLS = 10
    BLOCKS = 11
    NO_MOPPING_AREAS = 12
    OBSTACLES = 13
    IGNORED_OBSTACLES = 14
    OBSTACLES_WITH_PHOTO = 15
    IGNORED_OBSTACLES_WITH_PHOTO = 16
    CARPET_MAP = 17
    MOP_PATH = 18
    NO_CARPET_AREAS = 19
    DIGEST = 1024
    SIZE = 1024
    KNOWN_OBSTACLE_TYPES = {
        0: 'cable',
        2: 'shoes',
        3: 'poop',
        5: 'extension cord',
        9: 'weighting scale',
        10: 'clothes'
    }

    @staticmethod
    def parse(raw: bytes, colors: Colors, drawables: Drawables, texts: Texts, sizes: Sizes,
              image_config: ImageConfig, *args, **kwargs) -> MapData:
        map_data = MapData(25500, 1000)
        map_header_length = MapDataParserXiaomi.get_int16(raw, 0x02)
        map_data.major_version = MapDataParserXiaomi.get_int16(raw, 0x08)
        map_data.minor_version = MapDataParserXiaomi.get_int16(raw, 0x0A)
        map_data.map_index = MapDataParserXiaomi.get_int32(raw, 0x0C)
        map_data.map_sequence = MapDataParserXiaomi.get_int32(raw, 0x10)
        block_start_position = map_header_length
        img_start = None
        img_data = None
        while block_start_position < len(raw):
            block_header_length = MapDataParserXiaomi.get_int16(raw, block_start_position + 0x02)
            header = MapDataParserXiaomi.get_bytes(raw, block_start_position, block_header_length)
            block_type = MapDataParserXiaomi.get_int16(header, 0x00)
            block_data_length = MapDataParserXiaomi.get_int32(header, 0x04)
            block_data_start = block_start_position + block_header_length
            data = MapDataParserXiaomi.get_bytes(raw, block_data_start, block_data_length)

            if block_type == MapDataParserXiaomi.CHARGER:
                map_data.charger = MapDataParserXiaomi.parse_object_position(block_data_length, data)
            elif block_type == MapDataParserXiaomi.IMAGE:
                img_start = block_start_position
                img_data_length = block_data_length
                img_header_length = block_header_length
                img_data = data
                img_header = header
            elif block_type == MapDataParserXiaomi.ROBOT_POSITION:
                map_data.vacuum_position = MapDataParserXiaomi.parse_object_position(block_data_length, data)
            elif block_type == MapDataParserXiaomi.PATH:
                map_data.path = MapDataParserXiaomi.parse_path(block_start_position, header, raw)
            elif block_type == MapDataParserXiaomi.GOTO_PATH:
                map_data.goto_path = MapDataParserXiaomi.parse_path(block_start_position, header, raw)
            elif block_type == MapDataParserXiaomi.GOTO_PREDICTED_PATH:
                map_data.predicted_path = MapDataParserXiaomi.parse_path(block_start_position, header, raw)
            elif block_type == MapDataParserXiaomi.CURRENTLY_CLEANED_ZONES:
                map_data.zones = MapDataParserXiaomi.parse_zones(data, header)
            elif block_type == MapDataParserXiaomi.GOTO_TARGET:
                map_data.goto = MapDataParserXiaomi.parse_goto_target(data)
            elif block_type == MapDataParserXiaomi.DIGEST:
                map_data.is_valid = True
            elif block_type == MapDataParserXiaomi.VIRTUAL_WALLS:
                map_data.walls = MapDataParserXiaomi.parse_walls(data, header)
            elif block_type == MapDataParserXiaomi.NO_GO_AREAS:
                map_data.no_go_areas = MapDataParserXiaomi.parse_area(header, data)
            elif block_type == MapDataParserXiaomi.NO_MOPPING_AREAS:
                map_data.no_mopping_areas = MapDataParserXiaomi.parse_area(header, data)
            elif block_type == MapDataParserXiaomi.OBSTACLES:
                map_data.obstacles = MapDataParserXiaomi.parse_obstacles(data, header)
            elif block_type == MapDataParserXiaomi.IGNORED_OBSTACLES:
                map_data.ignored_obstacles = MapDataParserXiaomi.parse_obstacles(data, header)
            elif block_type == MapDataParserXiaomi.OBSTACLES_WITH_PHOTO:
                map_data.obstacles_with_photo = MapDataParserXiaomi.parse_obstacles(data, header)
            elif block_type == MapDataParserXiaomi.IGNORED_OBSTACLES_WITH_PHOTO:
                map_data.ignored_obstacles_with_photo = MapDataParserXiaomi.parse_obstacles(data, header)
            elif block_type == MapDataParserXiaomi.BLOCKS:
                block_pairs = MapDataParserXiaomi.get_int16(header, 0x08)
                map_data.blocks = MapDataParserXiaomi.get_bytes(data, 0, block_pairs)
            elif block_type == MapDataParserXiaomi.MOP_PATH:
                points_mask = MapDataParserXiaomi.get_bytes(raw, block_data_start, block_data_length)
                # only the map_data.path points where points_mask == 1 are in mop_path
                map_data.mop_path = MapDataParserXiaomi.parse_mop_path(map_data.path, points_mask)
            elif block_type == MapDataParserXiaomi.CARPET_MAP:
                data = MapDataParserXiaomi.get_bytes(raw, block_data_start, block_data_length)
                # only the indexes where value == 1 are in carpet_map
                map_data.carpet_map = MapDataParserXiaomi.parse_carpet_map(data, image_config)
            elif block_type == MapDataParserXiaomi.NO_CARPET_AREAS:
                map_data.no_carpet_areas = MapDataParserXiaomi.parse_area(header, data)
            else:
                _LOGGER.debug("UNKNOWN BLOCK TYPE: %s, header length %s, data length %s", block_type, block_header_length, block_data_length)
            block_start_position = block_start_position + block_data_length + MapDataParserXiaomi.get_int8(header, 2)

        if img_data:
            image, rooms = MapDataParserXiaomi.parse_image(img_data_length, img_header_length, img_data, img_header, map_data.carpet_map,
                                                           colors, image_config)
            map_data.image = image
            map_data.rooms = rooms

        if not map_data.image.is_empty:
            MapDataParserXiaomi.draw_elements(colors, drawables, sizes, map_data, image_config)
            if len(map_data.rooms) > 0 and map_data.vacuum_position is not None:
                map_data.vacuum_room = MapDataParserXiaomi.get_current_vacuum_room(img_start, raw,
                                                                                   map_data.vacuum_position)
            ImageHandlerXiaomi.rotate(map_data.image)
            ImageHandlerXiaomi.draw_texts(map_data.image, texts)
        return map_data

    @staticmethod
    def map_to_image(p: Point) -> Point:
        return Point(p.x / MM, p.y / MM)

    @staticmethod
    def image_to_map(x: float) -> float:
        return x * MM

    @staticmethod
    def get_current_vacuum_room(block_start_position: int, raw: bytes, vacuum_position: Point) -> int:
        block_header_length = MapDataParserXiaomi.get_int16(raw, block_start_position + 0x02)
        header = MapDataParserXiaomi.get_bytes(raw, block_start_position, block_header_length)
        block_data_length = MapDataParserXiaomi.get_int32(header, 0x04)
        block_data_start = block_start_position + block_header_length
        data = MapDataParserXiaomi.get_bytes(raw, block_data_start, block_data_length)
        image_top = MapDataParserXiaomi.get_int32(header, block_header_length - 16)
        image_left = MapDataParserXiaomi.get_int32(header, block_header_length - 12)
        image_width = MapDataParserXiaomi.get_int32(header, block_header_length - 4)
        p = MapDataParserXiaomi.map_to_image(vacuum_position)
        room = ImageHandlerXiaomi.get_room_at_pixel(data, image_width, round(p.x - image_left), round(p.y - image_top))
        return room

    @staticmethod
    def parse_image(block_data_length: int, block_header_length: int, data: bytes, header: bytes, carpet_map: Set[int],
                    colors: Colors, image_config: ImageConfig) -> Tuple[ImageData, Dict[int, Room]]:
        image_size = block_data_length
        image_top = MapDataParserXiaomi.get_int32(header, block_header_length - 16)
        image_left = MapDataParserXiaomi.get_int32(header, block_header_length - 12)
        image_height = MapDataParserXiaomi.get_int32(header, block_header_length - 8)
        image_width = MapDataParserXiaomi.get_int32(header, block_header_length - 4)
        if image_width \
                - image_width * (image_config[CONF_TRIM][CONF_LEFT] + image_config[CONF_TRIM][CONF_RIGHT]) / 100 \
                < MINIMAL_IMAGE_WIDTH:
            image_config[CONF_TRIM][CONF_LEFT] = 0
            image_config[CONF_TRIM][CONF_RIGHT] = 0
        if image_height \
                - image_height * (image_config[CONF_TRIM][CONF_TOP] + image_config[CONF_TRIM][CONF_BOTTOM]) / 100 \
                < MINIMAL_IMAGE_HEIGHT:
            image_config[CONF_TRIM][CONF_TOP] = 0
            image_config[CONF_TRIM][CONF_BOTTOM] = 0
        image, rooms_raw = ImageHandlerXiaomi.parse(data, image_width, image_height, carpet_map, colors, image_config)
        rooms = {}
        for number, room in rooms_raw.items():
            rooms[number] = Room(number, MapDataParserXiaomi.image_to_map(room[0] + image_left),
                                 MapDataParserXiaomi.image_to_map(room[1] + image_top),
                                 MapDataParserXiaomi.image_to_map(room[2] + image_left),
                                 MapDataParserXiaomi.image_to_map(room[3] + image_top))
        return ImageData(image_size,
                         image_top,
                         image_left,
                         image_height,
                         image_width,
                         image_config,
                         image, MapDataParserXiaomi.map_to_image), rooms

    @staticmethod
    def parse_carpet_map(data: bytes, image_config: ImageConfig) -> Set[int]:
        carpet_map = set()

        for i, v in enumerate(data):
            if v:
                carpet_map.add(i)
        return carpet_map

    @staticmethod
    def parse_goto_target(data: bytes) -> Point:
        x = MapDataParserXiaomi.get_int16(data, 0x00)
        y = MapDataParserXiaomi.get_int16(data, 0x02)
        return Point(x, y)

    @staticmethod
    def parse_object_position(block_data_length: int, data: bytes) -> Point:
        x = MapDataParserXiaomi.get_int32(data, 0x00)
        y = MapDataParserXiaomi.get_int32(data, 0x04)
        a = None
        if block_data_length > 8:
            a = MapDataParserXiaomi.get_int32(data, 0x08)
            if a > 0xFF:
                a = (a & 0xFF) - 256
        return Point(x, y, a)

    @staticmethod
    def parse_walls(data: bytes, header: bytes) -> List[Wall]:
        wall_pairs = MapDataParserXiaomi.get_int16(header, 0x08)
        walls = []
        for wall_start in range(0, wall_pairs * 8, 8):
            x0 = MapDataParserXiaomi.get_int16(data, wall_start + 0)
            y0 = MapDataParserXiaomi.get_int16(data, wall_start + 2)
            x1 = MapDataParserXiaomi.get_int16(data, wall_start + 4)
            y1 = MapDataParserXiaomi.get_int16(data, wall_start + 6)
            walls.append(Wall(x0, y0, x1, y1))
        return walls

    @staticmethod
    def parse_obstacles(data: bytes, header: bytes) -> List[Obstacle]:
        obstacle_pairs = MapDataParserXiaomi.get_int16(header, 0x08)
        obstacles = []
        if obstacle_pairs == 0:
            return obstacles
        obstacle_size = int(len(data) / obstacle_pairs)
        for obstacle_start in range(0, obstacle_pairs * obstacle_size, obstacle_size):
            x = MapDataParserXiaomi.get_int16(data, obstacle_start + 0)
            y = MapDataParserXiaomi.get_int16(data, obstacle_start + 2)
            details = {}
            if obstacle_size >= 6:
                details[ATTR_TYPE] = MapDataParserXiaomi.get_int16(data, obstacle_start + 4)
                if details[ATTR_TYPE] in MapDataParserXiaomi.KNOWN_OBSTACLE_TYPES:
                    details[ATTR_DESCRIPTION] = MapDataParserXiaomi.KNOWN_OBSTACLE_TYPES[details[ATTR_TYPE]]
                if obstacle_size >= 10:
                    u1 = MapDataParserXiaomi.get_int16(data, obstacle_start + 6)
                    u2 = MapDataParserXiaomi.get_int16(data, obstacle_start + 8)
                    details[ATTR_CONFIDENCE_LEVEL] = 0 if u2 == 0 else u1 * 10.0 / u2
                    if obstacle_size == 28 and (data[obstacle_start + 12] & 0xFF) > 0:
                        txt = MapDataParserXiaomi.get_bytes(data, obstacle_start + 12, 16)
                        details[ATTR_PHOTO_NAME] = txt.decode('ascii')
            obstacles.append(Obstacle(x, y, details))
        return obstacles

    @staticmethod
    def parse_zones(data: bytes, header: bytes) -> List[Zone]:
        zone_pairs = MapDataParserXiaomi.get_int16(header, 0x08)
        zones = []
        for zone_start in range(0, zone_pairs * 8, 8):
            x0 = MapDataParserXiaomi.get_int16(data, zone_start + 0)
            y0 = MapDataParserXiaomi.get_int16(data, zone_start + 2)
            x1 = MapDataParserXiaomi.get_int16(data, zone_start + 4)
            y1 = MapDataParserXiaomi.get_int16(data, zone_start + 6)
            zones.append(Zone(x0, y0, x1, y1))
        return zones

    @staticmethod
    def parse_path(block_start_position: int, header: bytes, raw: bytes) -> Path:
        path_points = []
        end_pos = MapDataParserXiaomi.get_int32(header, 0x04)
        point_length = MapDataParserXiaomi.get_int32(header, 0x08)
        point_size = MapDataParserXiaomi.get_int32(header, 0x0C)
        angle = MapDataParserXiaomi.get_int32(header, 0x10)
        start_pos = block_start_position + 0x14
        for pos in range(start_pos, start_pos + end_pos, 4):
            x = MapDataParserXiaomi.get_int16(raw, pos)
            y = MapDataParserXiaomi.get_int16(raw, pos + 2)
            path_points.append(Point(x, y))
        return Path(point_length, point_size, angle, [path_points])

    @staticmethod
    def parse_mop_path(path: Path, mask: bytes) -> Path:
        mop_paths = []
        points_num = 0
        for each_path in path.path:
            mop_path_points = []
            for i, point in enumerate(each_path):
                if mask[i]:
                    mop_path_points.append(point)
                    if (i + 1) < len(mask) and not mask[i + 1]:
                        points_num += len(mop_path_points)
                        mop_paths.append(mop_path_points)
                        mop_path_points = []

            points_num += len(mop_path_points)
            mop_paths.append(mop_path_points)
        return Path(points_num, path.point_size, path.angle, mop_paths)

    @staticmethod
    def parse_area(header: bytes, data: bytes) -> List[Area]:
        area_pairs = MapDataParserXiaomi.get_int16(header, 0x08)
        areas = []
        for area_start in range(0, area_pairs * 16, 16):
            x0 = MapDataParserXiaomi.get_int16(data, area_start + 0)
            y0 = MapDataParserXiaomi.get_int16(data, area_start + 2)
            x1 = MapDataParserXiaomi.get_int16(data, area_start + 4)
            y1 = MapDataParserXiaomi.get_int16(data, area_start + 6)
            x2 = MapDataParserXiaomi.get_int16(data, area_start + 8)
            y2 = MapDataParserXiaomi.get_int16(data, area_start + 10)
            x3 = MapDataParserXiaomi.get_int16(data, area_start + 12)
            y3 = MapDataParserXiaomi.get_int16(data, area_start + 14)
            areas.append(Area(x0, y0, x1, y1, x2, y2, x3, y3))
        return areas

    @staticmethod
    def get_bytes(data: bytes, start_index: int, size: int) -> bytes:
        return data[start_index: start_index + size]

    @staticmethod
    def get_int8(data: bytes, address: int) -> int:
        return data[address] & 0xFF

    @staticmethod
    def get_int16(data: bytes, address: int) -> int:
        return \
            ((data[address + 0] << 0) & 0xFF) | \
            ((data[address + 1] << 8) & 0xFFFF)

    @staticmethod
    def get_int32(data: bytes, address: int) -> int:
        return \
            ((data[address + 0] << 0) & 0xFF) | \
            ((data[address + 1] << 8) & 0xFFFF) | \
            ((data[address + 2] << 16) & 0xFFFFFF) | \
            ((data[address + 3] << 24) & 0xFFFFFFFF)
