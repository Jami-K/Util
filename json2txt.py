import json
import os

def labelme_to_yolo(json_path, output_dir, class_list):
    # Read the JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    image_width = data['imageWidth']
    image_height = data['imageHeight']
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Iterate through shapes in the JSON file
    for shape in data['shapes']:
        label = shape['label']
        if label not in class_list:
            continue
        
        # Get class index
        class_index = class_list.index(label)
        
        points = shape['points']
        
        # Calculate YOLO format bounding box coordinates
        x_min = min(point[0] for point in points)
        y_min = min(point[1] for point in points)
        x_max = max(point[0] for point in points)
        y_max = max(point[1] for point in points)
        
        x_center = (x_min + x_max) / 2 / image_width
        y_center = (y_min + y_max) / 2 / image_height
        width = (x_max - x_min) / image_width
        height = (y_max - y_min) / image_height
        
        # Create YOLO format annotation
        yolo_annotation = f"{class_index} {x_center} {y_center} {width} {height}\n"
        
        # Write annotation to file
        base_filename = os.path.splitext(os.path.basename(json_path))[0]
        output_file_path = os.path.join(output_dir, base_filename + '.txt')
        
        with open(output_file_path, 'a') as output_file:
            output_file.write(yolo_annotation)

def convert_directory(input_dir, output_dir, class_list):
    # Iterate over all files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            json_path = os.path.join(input_dir, filename)
            labelme_to_yolo(json_path, output_dir, class_list)

# Example usage
input_dir = '/home/nongshim/Label/burn/240125k/R/'
output_dir = '/home/nongshim/Label/burn/240125k/R/'
class_list = ['Empty', 'Reject']  # Replace with your actual class names

convert_directory(input_dir, output_dir, class_list)

