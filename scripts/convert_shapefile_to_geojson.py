#!/usr/bin/env python3
"""
Center Pivot Shapefile-to-GeoJSON Converter & Pad Localizer
Includes automated static booster station asset injection.
"""

import argparse
import json
import math
import os
import re
import sys
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon

# -----------------------------------------------------------------------------
# TRANSDUCER SCHEDULE & INVENTORY DATABASE
# -----------------------------------------------------------------------------
TRANSDUCER_REGISTRY = {
    "R-5 WEST": {"sn": "B53255-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 12.0},
    "R-5 EAST": {"sn": "B53250-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 10.0},
    "N-9":      {"sn": "B53223-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 850.0, "reg_psi": 15.0, "max_elev_diff": 14.0},
    "R-2":      {"sn": "B53200-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 825.0, "reg_psi": 15.0, "max_elev_diff": 6.0},
    "R-1":      {"sn": "B53224-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 8.0},
    "N-7":      {"sn": "B53249-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 850.0, "reg_psi": 15.0, "max_elev_diff": 16.0},
    "N-2":      {"sn": "B53746-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 900.0, "reg_psi": 15.0, "max_elev_diff": 18.0},
    "R-9":      {"sn": "B53235-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 5.0},
    "R-14":     {"sn": "B53704-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 775.0, "reg_psi": 15.0, "max_elev_diff": 9.0},
    "R-15":     {"sn": "B-53721-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 775.0, "reg_psi": 15.0, "max_elev_diff": 11.0},
    "R-16":     {"sn": "B53254-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 7.0},
    "N-8":      {"sn": "B51021-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 850.0, "reg_psi": 15.0, "max_elev_diff": 15.0},
    "N-6":      {"sn": "B-53754-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 900.0, "reg_psi": 15.0, "max_elev_diff": 20.0},
    "N-4":      {"sn": "B53755-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 900.0, "reg_psi": 15.0, "max_elev_diff": 14.0},
    "R-7":      {"sn": "B53252-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 8.0},
    "N-1":      {"sn": "B53703-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 850.0, "reg_psi": 15.0, "max_elev_diff": 10.0},
    "R-8":      {"sn": "B53764-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 7.0},
    "R-4":      {"sn": "B53706-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 9.0},
    "R-6":      {"sn": "B53246-B", "status": "Still Irrigating", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 6.0},
    "R-10":     {"sn": "B53251-B", "status": "Still Irrigating", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 8.0},
    "R-11":     {"sn": "B53213-B", "status": "Still Irrigating", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 10.0},
    "R-13":     {"sn": "B-51011-B", "status": "Still Irrigating", "z_rel": 6.50, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 7.0},
    "NEWELL-1": {"sn": "B53222-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 850.0, "reg_psi": 15.0, "max_elev_diff": 12.0},
    "R-12":     {"sn": "B53195-B", "status": "Complete", "z_rel": 6.83, "design_gpm": 800.0, "reg_psi": 15.0, "max_elev_diff": 9.0},
    "N-3":      {"sn": "B53809-B", "status": "Complete", "z_rel": 6.33, "design_gpm": 900.0, "reg_psi": 15.0, "max_elev_diff": 13.0},
    "N-5":      {"sn": "B53248-B", "status": "Complete", "z_rel": 6.50, "design_gpm": 900.0, "reg_psi": 15.0, "max_elev_diff": 17.0}
}

STATIC_INFRASTRUCTURE = [
    {
        "id": "Booster Station - Suction",
        "sn": "B53202-B",
        "status": "Active",
        "z_rel": 0.0,
        "design_gpm": 1200.0,
        "reg_psi": 0.0,
        "max_elev_diff": 0.0,
        "lat": 37.568544,
        "lon": -100.034103,
        "asset_type": "booster_station"
    },
    {
        "id": "Booster Station - Discharge",
        "sn": "B-53241-B",
        "status": "Active",
        "z_rel": 0.0,
        "design_gpm": 1200.0,
        "reg_psi": 0.0,
        "max_elev_diff": 0.0,
        "lat": 37.568544,
        "lon": -100.034103,
        "asset_type": "booster_station"
    }
]


def normalize_id(val: str) -> str:
    if not val:
        return ""
    s = str(val).strip().upper()
    s = re.sub(r'([-_A-Z\s]|^)0+([1-9]\d*)', r'\1\2', s)
    s = re.sub(r'\s*-\s*', '-', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def calculate_true_pivot_center_planar(geom_planar) -> Point:
    if geom_planar.geom_type == 'MultiPolygon':
        geom_planar = max(geom_planar.geoms, key=lambda a: a.area)

    coords = list(geom_planar.exterior.coords)
    segments = []

    for i in range(len(coords) - 1):
        p1 = coords[i]
        p2 = coords[i + 1]
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        segments.append((dist, p1, p2))

    segments.sort(key=lambda x: x[0], reverse=True)
    if len(segments) < 3:
        return geom_planar.centroid

    longest_dist, l1_p1, l1_p2 = segments[0]
    second_longest_dist, l2_p1, l2_p2 = segments[1]
    perimeter = geom_planar.length

    if longest_dist > perimeter * 0.10 and second_longest_dist > perimeter * 0.10:
        pts1 = [l1_p1, l1_p2]
        pts2 = [l2_p1, l2_p2]
        for pA in pts1:
            for pB in pts2:
                if math.hypot(pA[0] - pB[0], pA[1] - pB[1]) < 1.0:
                    return Point(pA[0], pA[1])

    return geom_planar.centroid


def convert_shapefile(input_shp_path: str, output_geojson_path: str, name_col: str = None):
    print(f"Reading input shapefile: {input_shp_path}")
    gdf = gpd.read_file(input_shp_path)

    gdf = gdf[gdf.geometry.notnull() & gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
    if gdf.empty:
        raise ValueError("No valid Polygon or MultiPolygon geometries found in file.")

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    if not name_col:
        cols = [c for c in gdf.columns if c.lower() != 'geometry']
        for candidate in ['NAME', 'FIELD_NAME', 'PIVOT_ID', 'ID', 'LABEL', 'PIVOT', 'IDENT']:
            matches = [c for c in cols if c.upper() == candidate]
            if matches:
                name_col = matches[0]
                break
        if not name_col:
            name_col = cols[0]

    gdf_planar = gdf.to_crs(epsg=3857)
    features = []

    # 1. Process Pivot Polygons
    for idx, row in gdf_planar.iterrows():
        raw_name = str(row.get(name_col, f"Pivot_{idx+1}")).strip()
        norm_key = normalize_id(raw_name)

        center_pad_planar = calculate_true_pivot_center_planar(row.geometry)
        pad_wgs = gpd.GeoSeries([center_pad_planar], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
        poly_wgs = gpd.GeoSeries([row.geometry], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]

        meta = TRANSDUCER_REGISTRY.get(norm_key, {
            "sn": str(row.get("SN", row.get("TRANSDUCER", "UNASSIGNED"))),
            "status": "Imported",
            "z_rel": 6.50,
            "design_gpm": 800.0,
            "reg_psi": 15.0,
            "max_elev_diff": 10.0
        })

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(pad_wgs.x, 7), round(pad_wgs.y, 7)]
            },
            "properties": {
                "id": raw_name,
                "norm_id": norm_key,
                "sn": meta["sn"],
                "status": meta["status"],
                "z_rel": meta["z_rel"],
                "design_gpm": meta["design_gpm"],
                "reg_psi": meta["reg_psi"],
                "max_elev_diff": meta["max_elev_diff"],
                "asset_type": "pivot",
                "polygon_geometry": poly_wgs.__geo_interface__
            }
        })

    # 2. Append Static Booster Station Points
    for asset in STATIC_INFRASTRUCTURE:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(asset["lon"], 7), round(asset["lat"], 7)]
            },
            "properties": {
                "id": asset["id"],
                "norm_id": normalize_id(asset["id"]),
                "sn": asset["sn"],
                "status": asset["status"],
                "z_rel": asset["z_rel"],
                "design_gpm": asset["design_gpm"],
                "reg_psi": asset["reg_psi"],
                "max_elev_diff": asset["max_elev_diff"],
                "asset_type": asset["asset_type"],
                "polygon_geometry": None
            }
        })

    geojson_payload = {
        "type": "FeatureCollection",
        "features": features
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_geojson_path)), exist_ok=True)
    with open(output_geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_payload, f, indent=2)

    print(f"Successfully processed {len(features)} total assets (including {len(STATIC_INFRASTRUCTURE)} booster stations).")
    print(f"Saved to: {output_geojson_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Pivot Shapefile to GeoJSON with True Pad Extraction")
    parser.add_argument("-i", "--input", required=True, help="Path to input shapefile (.shp) or GeoPackage (.gpkg)")
    parser.add_argument("-o", "--output", default="data/default_pivots.geojson", help="Output GeoJSON path")
    parser.add_argument("-n", "--name-field", default=None, help="Column name containing Pivot ID")

    args = parser.parse_args()
    convert_shapefile(args.input, args.output, args.name_field)
