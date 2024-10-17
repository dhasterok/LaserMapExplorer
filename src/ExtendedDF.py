import copy
import pandas as pd

class AttributeDataFrame(pd.DataFrame):
    """Creates a pandas DataFrame with custom attributes stored with each column.

    Create a dataframe with column attributes or add attributes to existing columns of a
    dataframe and methods to get and set them.

    Parameters
    ----------
    pandas.DataFrame : 
        Input dataframe, if none provided an empty dataframe can be created, defaults to None

    Methods
    -------
    attributes_to_dataframe :
        Return selected attributes of all columns in the AttributeDataFrame as a new DataFrame

    copy_columns :
        Extract specified columns into a new AttributeDataFrame, preserving their attributes

    match_attribute :
        Returns a list of columns where a specific attribute matches the given value

    get_attribute :
        Get an attribute from an AttributeDataFrame given a column or set of columns

    is_attribute :
        Checks to see if an attribute exists

    set_attribute :
        Get an attribute from an AttributeDataFrame

    show_attributes :
        Prints the attributes stored in the dataframe

    Returns
    -------
    AttributeDataFrame
        Adds column attributes and sets their values to a dataframe

    Examples
    --------
    Example 1: Creating the DataFrame with no initial data
    df = AttributeDataFrame()
    print(df)  # Output: Empty DataFrame

    # Adding data and attributes
    df['Temperature'] = [22, 23, 21]
    df.set_attribute('Temperature', 'units', 'Celsius')
    df.set_attribute('Temperature', 'average', 22)
    df.set_attribute('Temperature', 'uncertainty', 1)

    print(df)
    print(df.get_attribute('Temperature', 'units'))         # Output: Celsius
    print(df.get_attribute('Temperature', 'average'))       # Output: 22
    print(df.get_attribute('Temperature', 'uncertainty'))   # Output: 1

    Example 2: Creating the DataFrame from an existing dataframe
    
    #df = AttributeDataFrame(data, column_attributes=column_attributes)

    # Accessing attributes using methods
    #print(df.get_attribute('Temperature', 'units'))         # Output: Celsius
    #print(df.get_attribute('Pressure', 'average'))          # Output: 101

    # Setting new attributes
    #df.set_attribute('Temperature', 'range', (20, 25))
    #print(df.get_attribute('Temperature', 'range'))         # Output: (20, 25)
    """    
    _metadata = ['column_attributes']
    
    @property
    def _constructor(self):
        return AttributeDataFrame
    
    def __init__(self, data=None, *args, **kwargs):
        # Initialize column attributes
        self.column_attributes = kwargs.pop('column_attributes', {})
        
        # If no data is provided, initialize with an empty DataFrame
        if data is None:
            data = {}
        
        # Initialize the DataFrame
        super(AttributeDataFrame, self).__init__(data, *args, **kwargs)

    def __getitem__(self, key):
        result = super().__getitem__(key)
        if isinstance(result, pd.DataFrame):
            result.column_attributes = {
                col: self.column_attributes[col]
                for col in result.columns
                if col in self.column_attributes
            }
        return result
    
    def is_attribute(self, column, attribute):
        """
        Check if a given attribute exists for the specified column.

        Parameters
        ----------
        column : str
            The name of the column.
        attribute : str
            The attribute to check for.

        Returns
        -------
        bool
            True if the attribute exists for the column, False otherwise.
        """
        return column in self.column_attributes and attribute in self.column_attributes[column]

    def show_attributes(self, column=None):
        """Displays all attributes for a specific column or for the entire DataFrame."""
        if column:
            return self.column_attributes.get(column, {})
        return self.column_attributes
    
    def get_attribute(self, columns, attribute):
        """
        Get a single attribute from an AttributeDataFrame for one or more columns.

        Parameters
        ----------
        columns : str or list of str
            Name or list of column names.
        attribute : str
            Name of the attribute to retrieve.

        Returns
        -------
        any or list
            Attribute value(s). Returns a single value if one column is provided, 
            otherwise returns a list of attribute values for multiple columns.

        Examples
        --------
        df = AttributeDataFrame()
        df['Temperature'] = [22, 23, 21]
        df['Pressure'] = [101, 100, 102]
        df.set_attribute('Temperature', 'units', 'Celsius')
        df.set_attribute('Pressure', 'units', 'Pascal')

        # Single column
        print(df.get_attribute('Temperature', 'units'))  # Output: 'Celsius'

        # Multiple columns
        print(df.get_attribute(['Temperature', 'Pressure'], 'units'))  
        # Output: ['Celsius', 'Pascal']
        """
        if isinstance(columns, str):  # Handle single column input
            return self.column_attributes.get(columns, {}).get(attribute)
        
        # Handle multiple columns
        return [self.column_attributes.get(column, {}).get(attribute) for column in columns]

    def _set_attribute(self, column, attribute, value):
        """Set attribute of an AttributeDataFrame

        Adds an attribute to a dataframe

        Parameters
        ----------
        column : str
            Name of AttributeDataFrame column
        attribute : str
            Name of attribute
        value : any
            Value associated with attribute

        Examples
        --------
        df = AttributeDataFrame({'Temperature': [22, 23, 21], 'Pressure': [101, 102, 100]})
        df._set_attribute('Temperature', 'units', 'Celsius')
        df._set_attribute('Pressure', 'units', 'Pascal')
        df._set_attribute('Temperature', 'average', 22)
        df._set_attribute('Pressure', 'average', 101)
        """        
        if column not in self.column_attributes:
            self.column_attributes[column] = {}
        self.column_attributes[column][attribute] = value

    def set_attribute(self, columns, attribute, values):
        """
        Set an attribute for one or more columns.
        
        Parameters
        ----------
        columns : str or list
            A single column name or a list of column names.
        attribute : str
            The name of the attribute to set.
        values : any or list
            A single value to apply to all columns or a list of values for each column.

        Raises
        ------
        ValueError
            If the length of `columns` and `values` don't match when `values` is a list.

        Examples
        --------
        # Single column, single attribute value
        df.set_attribute('Temperature', 'units', 'Celsius')

        # Multiple columns, same attribute value
        df.set_attribute(['Temperature', 'Pressure'], 'source', 'Sensor')

        # Multiple columns, different attribute values
        df.set_attribute(['Temperature', 'Pressure'], 'units', ['Celsius', 'Pascal'])
        """
        # Case where a single column and a single value are provided
        if isinstance(columns, str) and not isinstance(values, list):
            self._set_attribute(columns, attribute, values)
        
        # Case where multiple columns and a list of values are provided
        elif isinstance(values, list):
            if len(columns) != len(values):
                raise ValueError("Length of columns and values must match when values is a list.")
            for col, val in zip(columns, values):
                self._set_attribute(col, attribute, val)
        
        # Case where multiple columns and a single value are provided
        else:
            for col in columns:
                self._set_attribute(col, attribute, values)
    
    def match_attribute(self, attribute, value):
        """
        Returns a list of columns where a specific attribute matches the given value.

        Parameters
        ----------
        attribute : str
            The attribute to search for.
        value : any, list
            The value(s) to match.

        Returns
        -------
        list
            A list of column names that have the attribute set to the specified value.
        """
        if isinstance(value, list):
            return [col for col, attrs in self.column_attributes.items() if attrs.get(attribute) in value]
        else:
            return [col for col, attrs in self.column_attributes.items() if attrs.get(attribute) == value]

    def match_attributes(self, attributes_dict):
        """
        Returns a list of columns where each attribute matches its corresponding value.

        Parameters
        ----------
        attributes_dict : dict
            A dictionary where keys are attribute names and values are the corresponding values to match.

        Returns
        -------
        list
            A list of column names where each attribute matches its corresponding value.
        """
        return [col for col, attrs in self.column_attributes.items()
                if all(attrs.get(attr) == val for attr, val in attributes_dict.items())]

    def get_attribute_dict(self, attribute_name):
        """
        Creates a dictionary from an attribute where the unique values of the attribute becomes the
        keys and the items are lists with the column names that match each attribute_name.

        Parameters
        ----------
        attribute_name : str
            Name of attribute within the `edf.column_attributes` dictionary.

        Returns
        -------
        dict
            A dictionary with attribute_values and columns that match.
        """

        # Initialize an empty dictionary
        attribute_dict = {}
        for k in self.column_attributes.keys():
            attribute = self.column_attributes[k].get(attribute_name)
            if attribute is None:
                attribute = 'none'

            if attribute not in attribute_dict:
                attribute_dict[attribute] = [k]
            else:
                attribute_dict[attribute].append(k)
        
        return attribute_dict

    def attributes_to_dataframe(self, attributes=None):
        """
        Return selected attributes of all columns in the AttributeDataFrame as a new DataFrame.

        Parameters
        ----------
        attributes : list, optional
            List of attributes to include in the resulting DataFrame. If None, all attributes
            will be included.

        Returns
        -------
        pandas.DataFrame
            DataFrame where each column corresponds to an original column in the
            AttributeDataFrame and each row corresponds to an attribute.

        Example
        -------
        df = AttributeDataFrame({'Temperature': [22, 23, 21], 'Pressure': [101, 102, 100]})
        df.set_attribute('Temperature', 'units', 'Celsius')
        df.set_attribute('Pressure', 'units', 'Pascal')
        df.set_attribute('Temperature', 'average', 22)
        df.set_attribute('Pressure', 'average', 101)

        # Get only the 'units' attribute
        attribute_df_units = df.attributes_to_dataframe(attributes=['units'])
        print(attribute_df_units)

        # Get both 'units' and 'average' attributes
        attribute_df_units_avg = df.attributes_to_dataframe(attributes=['units', 'average'])
        print(attribute_df_units_avg)
        """
        # Initialize a dictionary to store attributes
        attribute_dict = {}

        # Loop through each column in the AttributeDataFrame
        for column, col_attributes in self.column_attributes.items():
            # For each column, check if we are selecting specific attributes or including all
            for attr, value in col_attributes.items():
                if attributes is None or attr in attributes:
                    if attr not in attribute_dict:
                        attribute_dict[attr] = {}
                    attribute_dict[attr][column] = value

        # Create a DataFrame from the attributes dictionary
        return pd.DataFrame(attribute_dict).T  # Transpose to make columns correspond to original DataFrame columns

    def copy_columns(self, columns=None):
        """
        Extract specified columns into a new AttributeDataFrame, preserving their attributes.
        If no columns are specified, all columns will be copied.

        Parameters
        ----------
        columns : list, optional
            List of column names to extract. If None or empty, all columns are extracted.

        Returns
        -------
        AttributeDataFrame
            A new AttributeDataFrame containing the selected columns and their attributes.

        Example
        -------
        # Initialize an AttributeDataFrame
        df = AttributeDataFrame({'Temperature': [22, 23, 21], 'Pressure': [101, 102, 100]})
        df.set_attribute('Temperature', 'units', 'Celsius')
        df.set_attribute('Pressure', 'units', 'Pascal')
        df.set_attribute('Temperature', 'average', 22)
        df.set_attribute('Pressure', 'average', 101)

        # Extract all columns if no columns are specified
        new_df_all = df.copy_columns()
        print(new_df_all)
        print(new_df_all.get_attribute('Temperature', 'units'))   # Output: Celsius
        print(new_df_all.get_attribute('Pressure', 'units'))      # Output: Pascal
        """
        # If no columns are specified, copy all columns
        if columns is None or not columns:
            columns = self.columns

        # Check if the columns exist in the original DataFrame
        missing_columns = [col for col in columns if col not in self.columns]
        if missing_columns:
            raise ValueError(f"Columns not found in the original DataFrame: {missing_columns}")

        # Extract the selected columns' data
        new_df = self[columns].copy()

        # Create a new AttributeDataFrame with the selected columns
        new_attribute_df = AttributeDataFrame(new_df)

        # Copy the corresponding column attributes to the new DataFrame
        for column in columns:
            if column in self.column_attributes:
                new_attribute_df.column_attributes[column] = copy.deepcopy(self.column_attributes[column])

        return new_attribute_df
