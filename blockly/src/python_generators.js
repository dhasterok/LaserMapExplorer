/******************************
 * Python Generators for Custom Blocks
 ******************************/
// Import a generator.
import {pythonGenerator, Order} from 'blockly/python';
import { sample_ids } from './globals';
import {getCategorizedStyleDictCode} from './helper_functions'


// Python Generator: Load Directory
pythonGenerator.forBlock['load_directory'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    // self is instance of Workflow class
    var code = (dir_name === "'directory path'")
        ? 'self.main.io.open_directory(ui_update=False)\nself.store_sample_ids()\n'
        : 'self.main.io.open_directory(' + dir_name + ', ui_update=False)\nself.store_sample_ids()\n';
    return code;
};

pythonGenerator.forBlock['load_sample'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    var code = (dir_name === "'file path'")
        ? 'self.main.io.open_sample(ui_update=False)\nself.store_sample_ids()\n'
        : 'self.main.io.open_sample(' + dir_name + 'ui_update=False)\nself.store_sample_ids()\n';
    return code;
};


// Python Generator: Select Samples
pythonGenerator.forBlock['select_samples'] = function(block, generator) {
    var sample_id = generator.quote_(block.getFieldValue('SAMPLE_IDS'));
    var code = 'self.parent.change_sample(self.parent.sample_ids.index(' + sample_id + '))\n';
    return code;
};

pythonGenerator.forBlock['select_analytes'] = function(block) {
    var analyteSelectorValue = block.getFieldValue('analyteSelectorDropdown');
    var code = '';
    
    if (analyteSelectorValue === 'Current selection') {
        code = '';
    } else if (analyteSelectorValue === 'Analyte selector') {
        code = 'self.parent.open_select_analyte_dialog()\n';
        code += 'self.refresh_analyte_saved_lists_dropdown()\n'
    } else if (analyteSelectorValue === 'Saved lists') {''
        var savedListName = block.getFieldValue('analyteSavedListsDropdown');
        var quotedListName = generator.quote_(savedListName);
        code = 'self.parent.update_analyte_selection_from_file(' + quotedListName + ')\n';
    }
    code += 'self.main.update_blockly_field_types(self)'
    return code;
};
  
  
// Python code generator for the select_analytes block
pythonGenerator.forBlock['select_ref_val'] = function(block) {
    const refValue = block.getFieldValue('refValueDropdown'); // Get selected dropdown value
    const code = `self.parent.change_ref_material_BE('${refValue}')\n`; // Python function call
    return code;
};

pythonGenerator.forBlock['change_pixel_dimensions'] = function(block, generator) {
    var dx = block.getFieldValue('dx');
    var dy = block.getFieldValue('dy');
    var code = 'self.parent.data[self.parent.sample_id].update_resolution(dx ='+dx+ ', dy ='+ dy+', ui_update = False)\n';
    return code;
};


pythonGenerator.forBlock['swap_pixel_dimensions'] = function(block) {
    var code = 'self.parent.data[self.parent.sample_id].swap_resolution\n';
    return code;
};

pythonGenerator.forBlock['swap_x_y'] = function(block) {
    var code = 'self.parent.data[self.parent.sample_id].swap_xy\n';
    return code;
};

pythonGenerator.forBlock['select_outlier_method'] = function(block) {
    var method = block.getFieldValue('outlierMethodDropdown');
    var code = '';

    if (method === 'quantile criteria') {
        var uB = block.getFieldValue('uB');
        var lB = block.getFieldValue('lB');
        code += `self.parent.update_bounds(ub=${uB}, lb=${uB})\n`;
    }
    if (method === 'quantile and distance criteria') {
        var uB = block.getFieldValue('uB');
        var lB = block.getFieldValue('lB');
        var dUB = block.getFieldValue('dUB');
        var dLB = block.getFieldValue('dLB');
        code += `self.parent.update_bounds(ub=${uB}, lb=${uB}, d_ub=${dUB}, d_lb=${dLB})\n`;
    }
    
    code += `self.parent.data[self.parent.sample_id].outlier_method='${method}'\n`;
    return code;
};


pythonGenerator.forBlock['neg_handling_method'] = function(block) {
    var method = block.getFieldValue('negMethodDropdown');
    
     var code = `self.parent.data[self.parent.sample_id].negative_method='${method}'\n`;
    return code;
};

pythonGenerator.forBlock['select_custom_lists'] = function(block) {
    var analyteSelectorValue = block.getFieldValue('fieldSelectorDropdown');
    var code = '';
    
    if (analyteSelectorValue === 'Current selection') {
        code = '';
    } else if (analyteSelectorValue === 'Field selector') {
        code = 'self.parent.open_select_custom_field_dialog()\n';
    } else if (analyteSelectorValue === 'Saved lists') {
        var savedListName = block.getFieldValue('fieldSavedListsDropdown');
        var quotedListName = generator.quote_(savedListName);
        code = 'self.parent.update_analyte_selection_from_file(' + quotedListName + ')\n';
    }
    return code;
};



/*
// Python Generator: Sample IDs List
pythonGenerator.forBlock['sample_ids_list_block'] = function(block, generator) {
    const code = JSON.stringify(sample_ids);  // Generates Python list from global sample_ids variable
    return code;
};
*/
// Python Generator: Iterate Through Sample IDs
pythonGenerator.forBlock['loop_over_samples'] = function(block, generator) {
    var variable_sample_ids = JSON.stringify(sample_ids);
    var statements_do = generator.statementToCode(block, 'DO');
    var code = 'for field in ' + variable_sample_ids + ':\n' +
        generator.INDENT + 'self.parent.change_sample(self.parent.sample_ids.index(sample_id), save_analysis= False)\n' +
        statements_do;
    return code;
};


// Python Generator: Iterate Through Sample IDs
pythonGenerator.forBlock['loop_over_fields'] = function(block, generator) {
    var field_type = block.plotType ? generator.quote_(block.fieldType) : 'Analyte';
    var statements_do = generator.statementToCode(block, 'DO');
    var code = 'for field in get_field_list(' + field_type + '):\n' +
        statements_do;
    return code;
};

pythonGenerator.forBlock['plot_map'] = function(block, generator) {
    // Retrieve the stored fieldType from the block
    const field_type = generator.quote_(block.getFieldValue('fieldType'));
    // Retrieve the stored field from the block
    const field = generator.quote_(block.getFieldValue('field'));

    const plot_type = generator.quote_('analyte map');
    let code = '';
    code += `axes_dict = {}\n`;
    code += `text_dict = {}\n`;
    code += `markers_dict = {}\n`;
    code += `colors_dict = {}\n`;
    code += '\n';
    
    // Insert sub-block statements
    let subBlocksCode = generator.statementToCode(block, 'Styling') || ''

    // remove *all* leading spaces:
    subBlocksCode = subBlocksCode.replace(/^ +/gm, '');

    code += subBlocksCode + '\n';
  
    // Merge them into style_dict
    code += `style_dict = {}\n`;
    code += `if axes_dict:\n`;
    code += `    style_dict["Axes"] = axes_dict\n`;
    code += `if text_dict:\n`;
    code += `    style_dict["Text"] = text_dict\n`;
    code += `if markers_dict:\n`;
    code += `    style_dict["Markers"] = markers_dict\n`;
    code += `if colors_dict:\n`;
    code += `    style_dict["Colors"] = colors_dict\n\n`;
  
    // update self.parent.style.style_dict with `style_dict`
    code += `if (style_dict):\n` +
    generator.INDENT +`self.main.plot_style.style_dict[${plot_type}] = {**self.main.plot_style.style_dict[${plot_type}], **style_dict}\n`+
    generator.INDENT +`self.main.plot_style.set_style_dictionary(${plot_type})\n`;
    code += `self.main.plot_map_mpl(self.main.sample_id, field_type = ${field_type},field = ${field})\n`;
    code += `self.main.plot_viewer.show()`
    return code;
};


pythonGenerator.forBlock['plot'] = function(block, generator) {
    // Retrieve the stored plotType from the block
    var plot_type = block.plotType ? generator.quote_(block.plotType) : 'None';

    // Initialize an empty code string
    var code = '';

    // Check if a `style` block is connected
    var styleCode = generator.valueToCode(block, 'style', Order.NONE);
    if (styleCode && styleCode !== '{}') {
        code += `
self.parent.plot_style.style_dict[${plot_type}] = {**self.parent.plot_style.style_dict[${plot_type}], **${styleCode}}
self.parent.plot_style.set_style_widgets(${plot_type})
`;
    }

    // Update the visualization regardless of the style connection
    code += `self.parent.update_SV(${plot_type})\n`;
    return code;
};


////// Style blocks ////////////
// Assuming you have a pythonGenerator object (like Blockly.Python or similar)
// we define forBlock[...] for each new block type:

/***********************************************
 * X Axis Block (Statement)
 ***********************************************/
pythonGenerator.forBlock['x_axis'] = function(block, generator) {
// 1) Gather user inputs
const rawXLabel = block.getFieldValue('xLabel');
const xLabel = rawXLabel ? generator.quote_(rawXLabel) : null;  // skip if blank
const xLimMin = block.getFieldValue('xLimMin') || 'None';
const xLimMax = block.getFieldValue('xLimMax') || 'None';
const rawXScale = block.getFieldValue('xScaleDropdown');
const xScale = rawXScale ? generator.quote_(rawXScale) : null;   // skip if blank?

// 2) Build a partial dict in Python. We'll call it `tmp_dict` and merge it into `axes_dict`.
// Conditionally add lines if non-empty.
const codeLines = [];
if (xLabel)    codeLines.push(`"XLabel": ${xLabel}`);
if (xLimMin || xLimMax) {
    // At least one limit is specified (even if 'None')
    codeLines.push(`"XLim": [${xLimMin}, ${xLimMax}]`);
}
if (xScale)    codeLines.push(`"XScale": ${xScale}`);

// If the user left everything blank, we might not add anything
if (codeLines.length === 0) {
    // Return empty code if there's truly nothing to update
    return '# x_axis block: no fields set\n';
}

// 3) Construct statement code
let code = '# x_axis block\n';
code += 'tmp_dict = {\n';
code += '  ' + codeLines.join(',\n  ') + '\n';
code += '}\n';
code += 'axes_dict.update(tmp_dict)\n\n';
return code;
};
  
  
  /***********************************************
   * Y Axis Block (Statement)
   ***********************************************/

  
pythonGenerator.forBlock['y_axis'] = function(block, generator) {
    const rawYLabel = block.getFieldValue('yLabel');
    const yLabel = rawYLabel ? generator.quote_(rawYLabel) : null;
    const yLimMin = block.getFieldValue('yLimMin') || 'None';
    const yLimMax = block.getFieldValue('yLimMax') || 'None';
    const rawYScale = block.getFieldValue('yScaleDropdown');
    const yScale = rawYScale ? generator.quote_(rawYScale) : null;

    const codeLines = [];
    if (yLabel)    codeLines.push(`"YLabel": ${yLabel}`);
    if (yLimMin || yLimMax) {
        codeLines.push(`"YLim": [${yLimMin}, ${yLimMax}]`);
    }
    if (yScale)    codeLines.push(`"YScale": ${yScale}`);

    if (codeLines.length === 0) {
        return '# y_axis block: no fields set\n';
    }

    let code = '# y_axis block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    code += 'axes_dict.update(tmp_dict)\n\n';
    return code;
};
  
  
  /***********************************************
   * Z Axis, C Axis, etc.
   ***********************************************/
  // Repeat the same pattern, each updating `axes_dict` if you want them all in "Axes"
  // or separate them if c_axis is conceptually different.
  pythonGenerator.forBlock['z_axis'] = function(block, generator) {
    const rawZLabel = block.getFieldValue('zLabel');
    const zLabel = rawZLabel ? generator.quote_(rawZLabel) : null;
    const zLimMin = block.getFieldValue('zLimMin') || 'None';
    const zLimMax = block.getFieldValue('zLimMax') || 'None';
    const rawZScale = block.getFieldValue('zScaleDropdown');
    const zScale = rawZScale ? generator.quote_(rawZScale) : null;
  
    const codeLines = [];
    if (zLabel)  codeLines.push(`"ZLabel": ${zLabel}`);
    if (zLimMin || zLimMax) {
      codeLines.push(`"ZLim": [${zLimMin}, ${zLimMax}]`);
    }
    if (zScale)  codeLines.push(`"ZScale": ${zScale}`);
  
    if (codeLines.length === 0) {
      return '# z_axis block: no fields set\n';
    }
  
    let code = '# z_axis block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    code += 'axes_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  pythonGenerator.forBlock['c_axis'] = function(block, generator) {
    const rawCLabel = block.getFieldValue('cLabel');
    const cLabel = rawCLabel ? generator.quote_(rawCLabel) : null;
    const cLimMin = block.getFieldValue('cLimMin') || 'None';
    const cLimMax = block.getFieldValue('cLimMax') || 'None';
    const rawCScale = block.getFieldValue('cScaleDropdown');
    const cScale = rawCScale ? generator.quote_(rawCScale) : null;
  
    const codeLines = [];
    if (cLabel) codeLines.push(`"CLabel": ${cLabel}`);
    if (cLimMin || cLimMax) {
      codeLines.push(`"CLim": [${cLimMin}, ${cLimMax}]`);
    }
    if (cScale) codeLines.push(`"CScale": ${cScale}`);
  
    if (codeLines.length === 0) {
      return '# c_axis block: no fields set\n';
    }
  
    let code = '# c_axis block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    code += 'axes_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  
  /***********************************************
   * Font Block => text_dict
   ***********************************************/
  
  pythonGenerator.forBlock['font'] = function(block, generator) {
    const rawFont = block.getFieldValue('font');
    const font = rawFont ? generator.quote_(rawFont) : null;
    const rawFontSize = block.getFieldValue('fontSize');
    const fontSize = rawFontSize ? rawFontSize : 'None';
  
    const codeLines = [];
    if (font)     codeLines.push(`"Font": ${font}`);
    if (fontSize !== 'None') codeLines.push(`"FontSize": ${fontSize}`);
  
    if (codeLines.length === 0) {
      return '# font block: no fields set\n';
    }
  
    let code = '# font block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    code += 'text_dict.update(tmp_dict)\n\n';  // goes to text_dict
    return code;
  };
  
  
  /***********************************************
   * Tick Direction => maybe in Axes
   ***********************************************/
  pythonGenerator.forBlock['tick_direction'] = function(block, generator) {
    const rawTickDir = block.getFieldValue('tickDirectionDropdown');
    const tickDir = rawTickDir ? generator.quote_(rawTickDir) : null;
  
    if (!tickDir) {
      return '# tick_direction block: no fields set\n';
    }
  
    let code = '# tick_direction block\n';
    code += `tmp_dict = {\n`;
    code += `  "TickDir": ${tickDir}\n`;
    code += `}\n`;
    code += `axes_dict.update(tmp_dict)\n\n`;
    return code;
  };
  
  
  /***********************************************
   * Aspect Ratio => also Axes
   ***********************************************/
  pythonGenerator.forBlock['aspect_ratio'] = function(block, generator) {
    const rawTickDir = block.getFieldValue('tickDirectionDropdown');
    const tickDir = rawTickDir ? generator.quote_(rawTickDir) : null;
    const rawAspect = block.getFieldValue('aspectRatio') || '';
    const aspectRatio = rawAspect ? rawAspect : 'None';
  
    // If user typed nothing for tickDir and aspectRatio, skip
    if (!tickDir && (!rawAspect || rawAspect.trim() === '')) {
      return '# aspect_ratio block: no fields set\n';
    }
  
    let code = '# aspect_ratio block\n';
    code += `tmp_dict = {\n`;
    if (tickDir) code += `  "TickDir": ${tickDir},\n`;
    code += `  "AspectRatio": ${aspectRatio}\n`;
    code += `}\n`;
    code += `axes_dict.update(tmp_dict)\n\n`;
    return code;
  };
  
  
  /***********************************************
   * Coloring => colors_dict
   ***********************************************/
  pythonGenerator.forBlock['coloring'] = function(block, generator) {
    const rawMap = block.getFieldValue('colormap');
    const colormap = rawMap ? generator.quote_(rawMap) : null;
  
    if (!colormap) {
      return '# coloring block: no fields set\n';
    }
  
    let code = '# coloring block\n';
    code += `tmp_dict = {\n`;
    code += `  "Colormap": ${colormap}\n`;
    code += `}\n`;
    code += `colors_dict.update(tmp_dict)\n\n`;
    return code;
  };
  
  
  /***********************************************
   * Add Scale => text_dict or maybe Axes? 
   ***********************************************/
  pythonGenerator.forBlock['add_scale'] = function(block, generator) {
    const rawScaleColor = block.getFieldValue('scaleColor');
    const scaleColor = rawScaleColor ? generator.quote_(rawScaleColor) : null;
    const rawScaleUnits = block.getFieldValue('scaleUnits');
    const scaleUnits = rawScaleUnits ? generator.quote_(rawScaleUnits) : null;
    const scaleLength = block.getFieldValue('scaleLength') || 'None';
    const rawScaleDir = block.getFieldValue('scaleDirection');
    const scaleDirection = rawScaleDir ? generator.quote_(rawScaleDir) : null;
  
    let codeLines = [];
    if (scaleColor) codeLines.push(`"ScaleColor": ${scaleColor}`);
    if (scaleUnits) codeLines.push(`"ScaleUnits": ${scaleUnits}`);
    // We'll allow scaleLength even if it's 'None'
    codeLines.push(`"ScaleLength": ${scaleLength}`);
    if (scaleDirection) codeLines.push(`"ScaleDirection": ${scaleDirection}`);
  
    // If everything is default, skip
    if (codeLines.length === 1 && codeLines[0].includes('ScaleLength')) {
      // Means user didn't set anything but scaleLength is forced to 'None'
      return '# add_scale block: no meaningful fields set\n';
    }
  
    let code = '# add_scale block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    // Suppose we treat scale info as "Text"
    code += 'text_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  
  /***********************************************
   * Marker Properties => markers_dict
   ***********************************************/
  pythonGenerator.forBlock['marker_properties'] = function(block, generator) {
    const rawSymbol = block.getFieldValue('markerSymbol');
    const markerSymbol = rawSymbol ? generator.quote_(rawSymbol) : null;
    const markerSize = block.getFieldValue('markerSize') || 'None';
    const rawColor = block.getFieldValue('markerColor');
    const markerColor = rawColor ? generator.quote_(rawColor) : null;
  
    let codeLines = [];
    if (markerSymbol) codeLines.push(`"MarkerSymbol": ${markerSymbol}`);
    codeLines.push(`"MarkerSize": ${markerSize}`); // always add, even if 'None'
    if (markerColor) codeLines.push(`"MarkerColor": ${markerColor}`);
  
    if (codeLines.length === 1 && codeLines[0].includes('MarkerSize')) {
      // Means user typed no symbol nor color
      // We might skip if it's all blank
      return '# marker_properties block: no fields set\n';
    }
  
    let code = '# marker_properties block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    code += 'markers_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  
  /***********************************************
   * Line Properties => markers_dict or a separate lines_dict
   ***********************************************/
  pythonGenerator.forBlock['line_properties'] = function(block, generator) {
    const lineWidth = block.getFieldValue('lineWidth') || 'None';
    const rawLineColor = block.getFieldValue('lineColor');
    const lineColor = rawLineColor ? generator.quote_(rawLineColor) : null;
  
    let codeLines = [];
    codeLines.push(`"LineWidth": ${lineWidth}`);
    if (lineColor) codeLines.push(`"LineColor": ${lineColor}`);
  
    if (codeLines.length === 1 && codeLines[0].includes('LineWidth')) {
      // means user typed no color
      // skip if it's all default
      return '# line_properties block: no fields set\n';
    }
  
    let code = '# line_properties block\n';
    code += 'tmp_dict = {\n';
    code += '  ' + codeLines.join(',\n  ') + '\n';
    code += '}\n';
    code += 'markers_dict.update(tmp_dict)\n\n'; 
    // or lines_dict.update if you prefer a separate dict
    return code;
  };
  
  
  /***********************************************
   * Color Field => colors_dict
   ***********************************************/
  pythonGenerator.forBlock['color_field'] = function(block, generator) {
    const rawFieldType = block.getFieldValue('fieldType');
    const fieldType = rawFieldType ? generator.quote_(rawFieldType) : null;
    const rawField = block.getFieldValue('field');
    const field = rawField ? generator.quote_(rawField) : null;
  
    if (!fieldType && !field) {
      return '# color_field block: no fields set\n';
    }
  
    let code = '# color_field block\n';
    code += 'tmp_dict = {\n';
    if (fieldType) code += `  "FieldType": ${fieldType},\n`;
    if (field)     code += `  "Field": ${field},\n`;
    code = code.replace(/,\n$/, '\n');  // remove trailing comma
    code += '}\n';
    code += 'colors_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  
  /***********************************************
   * Colormap => colors_dict
   ***********************************************/
  pythonGenerator.forBlock['colormap'] = function(block, generator) {
    const cm = block.getFieldValue('colormap');
    const rawCM = cm ? generator.quote_(cm) : null;
    const reverse = block.getFieldValue('reverse') === 'TRUE';
    const directionVal = block.getFieldValue('direction');
    const direction = directionVal ? generator.quote_(directionVal) : null;
  
    if (!rawCM && !direction && !reverse) {
      return '# colormap block: no fields set\n';
    }
  
    let code = '# colormap block\n';
    code += 'tmp_dict = {\n';
    if (rawCM)    code += `  "Colormap": ${rawCM},\n`;
    if (reverse)  code += `  "Reverse": true,\n`; 
    if (direction) code += `  "Direction": ${direction},\n`;
    code = code.replace(/,\n$/, '\n'); // remove trailing comma
    code += '}\n';
    code += 'colors_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  
  /***********************************************
   * Show Mass => colors_dict or markers_dict or up to you
   ***********************************************/
  pythonGenerator.forBlock['show_mass'] = function(block, generator) {
    const showMass = block.getFieldValue('showMass') === 'TRUE';
  
    if (!showMass) {
      return '# show_mass block: user disabled\n';
    }
  
    // If user checked TRUE, we add "ShowMass": true
    let code = '# show_mass block\n';
    code += 'tmp_dict = {\n';
    code += `  "ShowMass": true\n`;
    code += '}\n';
    code += 'colors_dict.update(tmp_dict)\n\n';
    return code;
  };
  
  
  /***********************************************
   * Color By Cluster => colors_dict
   ***********************************************/
  pythonGenerator.forBlock['color_by_cluster'] = function(block, generator) {
    const rawCluster = block.getFieldValue('clusterType');
    const clusterType = rawCluster ? generator.quote_(rawCluster) : null;
  
    if (!clusterType) {
      return '# color_by_cluster block: no fields set\n';
    }
  
    let code = '# color_by_cluster block\n';
    code += 'tmp_dict = {\n';
    code += `  "ClusterType": ${clusterType}\n`;
    code += '}\n';
    code += 'colors_dict.update(tmp_dict)\n\n';
    return code;
  };
  



pythonGenerator.forBlock['styles'] = function(block, generator) {
    // Retrieve code for each connected sub-block, default to an empty object if not connected
    var axisAndLabelsCode = generator.valueToCode(block, 'axis_and_labels', Order.NONE);
    var annotAndScaleCode = generator.valueToCode(block, 'annot_and_scale', Order.NONE);
    var marksAndLinesCode = generator.valueToCode(block, 'markers_and_lines', Order.NONE);
    var coloringCode = generator.valueToCode(block, 'coloring', Order.NONE);

    // Construct the style dictionary with only non-empty entries
    var styleDict = [];
    if (axisAndLabelsCode && axisAndLabelsCode !== '{}') styleDict.push(`"Axes": ${axisAndLabelsCode}`);
    if (annotAndScaleCode && annotAndScaleCode !== '{}') styleDict.push(`"Text": ${annotAndScaleCode}`);
    if (marksAndLinesCode && marksAndLinesCode !== '{}') styleDict.push(`"Markers": ${marksAndLinesCode}`);
    if (coloringCode && coloringCode !== '{}') styleDict.push(`"Colors": ${coloringCode}`);

    // Assemble the dictionary as a string, ensuring only non-empty values are included
    var code = `{${styleDict.join(', ')}}`;
    
    return [code, Order.ATOMIC];
};




pythonGenerator.forBlock['axis_and_labels'] = function(block, generator) {
    const xLabel = generator.quote_(block.getFieldValue('xLabel'));
    const xLimMin = block.getFieldValue('xLimMin');
    const xLimMax = block.getFieldValue('xLimMax');
    const xScale = generator.quote_(block.getFieldValue('xScaleDropdown'));
    const yLabel = generator.quote_(block.getFieldValue('yLabel'));
    const yLimMin = block.getFieldValue('yLimMin');
    const yLimMax = block.getFieldValue('yLimMax');
    const yScale = generator.quote_(block.getFieldValue('yScaleDropdown'));
    const zLabel = generator.quote_(block.getFieldValue('zLabel'));
    const tickDirection = generator.quote_(block.getFieldValue('tickDirectionDropdown'));

    const code = `
{
    "XLabel": ${xLabel},
    "XLim": [${xLimMin}, ${xLimMax}],
    "XScale": ${xScale},
    "YLabel": ${yLabel},
    "YLim": [${yLimMin}, ${yLimMax}],
    "YScale": ${yScale},
    "ZLabel": ${zLabel},
    "TickDir": ${tickDirection}
}`;
    return [code, Order.ATOMIC];
};

pythonGenerator.forBlock['annot_and_scale'] = function(block, generator) {
    const scaleDirection = generator.quote_(block.getFieldValue('scaleDirection'));
    const scaleLocation = generator.quote_(block.getFieldValue('scaleLocation'));
    const scaleLength = block.getFieldValue('scaleLength') || 'None';
    const overlayColor = generator.quote_(block.getFieldValue('overlayColor'));
    const font = generator.quote_(block.getFieldValue('font'));
    const fontSize = block.getFieldValue('fontSize');
    const showMass = block.getFieldValue('showMass') === 'TRUE';

    const code = `
{
    "Direction": ${scaleDirection},
    "Location": ${scaleLocation},
    "Length": ${scaleLength},
    "OverlayColor": ${overlayColor},
    "Font": ${font},
    "FontSize": ${fontSize},
    "ShowMass": ${showMass}
}`;
    return [code,Order.ATOMIC];
};

pythonGenerator.forBlock['marks_and_lines'] = function(block, generator) {
    const symbol = generator.quote_(block.getFieldValue('symbol'));
    const size = block.getFieldValue('size');
    const transparency = block.getFieldValue('transparency');
    const lineWidth = generator.quote_(block.getFieldValue('lineWidth'));
    const lineColor = generator.quote_(block.getFieldValue('lineColor'));
    const lengthMultiplier = block.getFieldValue('lengthMultiplier');

    const code = `
{
    "Symbol": ${symbol},
    "Size": ${size},
    "Alpha": ${transparency},
    "LineWidth": ${lineWidth},
    "Color": ${lineColor},
    "Multiplier": ${lengthMultiplier}
}`;
    return [code, Order.ATOMIC];
};

pythonGenerator.forBlock['coloring'] = function(block, generator) {
    const colorByField = generator.quote_(block.getFieldValue('colorByField'));
    const field = generator.quote_(block.getFieldValue('field'));
    const resolution = block.getFieldValue('resolution');
    const colormap = generator.quote_(block.getFieldValue('colormap'));
    const reverse = block.getFieldValue('reverse') === 'TRUE';
    const scale = generator.quote_(block.getFieldValue('scale'));
    const cLimMin = block.getFieldValue('cLimMin');
    const cLimMax = block.getFieldValue('cLimMax');
    const cBarLabel = generator.quote_(block.getFieldValue('cBarLabel'));
    const cBarDirection = generator.quote_(block.getFieldValue('cBarDirection'));

    const code = `
{
    "ColorByField": ${colorByField},
    "Field": ${field},
    "Resolution": ${resolution},
    "Colormap": ${colormap},
    "Reverse": ${reverse},
    "Scale": ${scale},
    "CLim": [${cLimMin}, ${cLimMax}],
    "CBarLabel": ${cBarLabel},
    "CBarDirection": ${cBarDirection}
}`;
    return [code, Order.ATOMIC];
};

