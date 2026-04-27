import csv

def create_csv(filename):
    # Sample data: list of rows (each row is a list of values)
    data = [
        ["Name", "Age", "City"],  # Header row
        ["Alice", 30, "New York"],
        ["Bob", 25, "Los Angeles"],
        ["Charlie", 35, "Chicago"]
    ]
    
    try:
        # Open file in write mode with newline='' to avoid blank lines on Windows
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write each row to the CSV file
            writer.writerows(data)
        
        print(f"CSV file '{filename}' created successfully.")
    
    except IOError as e:
        print(f"Error writing to file: {e}")

# Create the CSV file
create_csv("people.csv")
