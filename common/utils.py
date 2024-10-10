def convert_genres(list_input):
    # Step 1: Join characters into a string
    joined_string = "".join(list_input)

    # Step 2: Strip curly braces and split by comma
    genres_list = joined_string.strip("{}").split(",")

    # Step 3: Remove any extra spaces (if any) and clean the items
    genres_list = [genre.strip() for genre in genres_list]

    return genres_list
