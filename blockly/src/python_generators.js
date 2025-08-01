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
        ? 'self.io.open_directory()\nself.store_sample_ids()\n'
        : 'self.io.open_directory(' + dir_name + ', )\nself.store_sample_ids()\n';
    code += 'self.io.initialize_sample_object(self.outlier_method, self.negative_method)\n';  
    return code;
};

pythonGenerator.forBlock['load_sample'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    var code = (dir_name === "'file path'")
        ? 'self.io.open_sample()\nself.store_sample_ids()\n'
        : 'self.io.open_sample(' + dir_name + ')\nself.store_sample_ids()\n'
        
    code += 'self.io.initialize_sample_object(self.outlier_method, self.negative_method)\n';  
    return code;
};


// Python Generator: Select Samples
pythonGenerator.forBlock['select_samples'] = function(block, generator) {
    var sample_id = generator.quote_(block.getFieldValue('SAMPLE_IDS'));
    var code = 'self.change_sample(self.app_data.sample_list.index(' + sample_id + '))\n';
    return code;
};

pythonGenerator.forBlock['select_analytes'] = function(block,generator) {
    var analyteSelectorValue = block.getFieldValue('analyteSelectorDropdown');
    var code = '';
    
    if (analyteSelectorValue === 'Current selection') {
        code = '';
    } else if (analyteSelectorValue === 'Analyte selector') {
        code = 'self.open_select_analyte_dialog()\n';
        code += `self.refresh_saved_lists_dropdown('Analyte')\n`
    } else if (analyteSelectorValue === 'Saved lists') {''
        var savedListName = block.getFieldValue('analyteSavedListsDropdown');
        var quotedListName = generator.quote_(savedListName);
        code = 'self.update_analyte_selection_from_file(' + quotedListName + ')\n';
    }
    code += 'self.update_blockly_field_types(self)'
    return code;
};
  
pythonGenerator.forBlock['select_field_from_type'] = function(block, generator) {
  // 1) Retrieve the user-chosen values
  const fieldTypeValue = block.getFieldValue('fieldType') || '';
  const fieldValue     = block.getFieldValue('field') || '';

  // 2) Build some Python statements
  //    For example, maybe we call a Python method 'select_field'
  //    with the chosen fieldType and field. Adjust as needed:
  let code = '';

  // If user left it at default ('' or 'Select...'), skip
  if (fieldValue !== '' && fieldValue !== 'Select...') {
    const quotedFieldType = generator.quote_(fieldTypeValue);
    const quotedField     = generator.quote_(fieldValue);

    code += `# select_field_from_type block\n`;
    code += `self.select_field_from_type(${quotedFieldType}, ${quotedField})\n`;
  } else {
    code += `# select_field_from_type block: no field selected\n`;
  }

  // 3) Return statement code
  return code;
}; 



// Python code generator for the select_analytes block
pythonGenerator.forBlock['select_ref_val'] = function(block) {
    const refValue = block.getFieldValue('refValueDropdown'); // Get selected dropdown value
    const code = `self.change_ref_material_BE('${refValue}')\n`; // Python function call
    return code;
};

pythonGenerator.forBlock['change_pixel_dimensions'] = function(block, generator) {
    var dx = block.getFieldValue('dx');
    var dy = block.getFieldValue('dy');
    var code = 'self.data[self.app_data.sample_id].update_resolution(dx ='+dx+ ', dy ='+ dy+')\n';
    return code;
};


pythonGenerator.forBlock['swap_pixel_dimensions'] = function(block) {
    var code = 'self.data[self.app_data.sample_id].swap_resolution\n';
    return code;
};

pythonGenerator.forBlock['swap_x_y'] = function(block) {
    var code = 'self.data[self.app_data.sample_id].swap_xy\n';
    return code;
};

pythonGenerator.forBlock['select_outlier_method'] = function(block) {
    var method = block.getFieldValue('outlierMethodDropdown');
    var code = '';

    if (method === 'quantile criteria') {
        var uB = block.getFieldValue('uB');
        var lB = block.getFieldValue('lB');
        code += `self.update_bounds(ub=${uB}, lb=${uB})\n`;
    }
    if (method === 'quantile and distance criteria') {
        var uB = block.getFieldValue('uB');
        var lB = block.getFieldValue('lB');
        var dUB = block.getFieldValue('dUB');
        var dLB = block.getFieldValue('dLB');
        code += `self.update_bounds(ub=${uB}, lb=${uB}, d_ub=${dUB}, d_lb=${dLB})\n`;
    }
    
    code += `self.data[self.app_data.sample_id].outlier_method='${method}'\n`;
    return code;
};


pythonGenerator.forBlock['neg_handling_method'] = function(block) {
    var method = block.getFieldValue('negMethodDropdown');
    
     var code = `self.data[self.app_data.sample_id].negative_method='${method}'\n`;
    return code;
};

pythonGenerator.forBlock['select_fields_list'] = function(block,generator) {
    var fieldSelectorDropdownValue = block.getFieldValue('fieldSelectorDropdown');
    var code = '';
    
    if (fieldSelectorDropdownValue === 'Current selection') {
        code = '';
    } else if (fieldSelectorDropdownValue === 'Field selector') {
        code = 'self.open_field_selector_dialog()\n';
    } else if (fieldSelectorDropdownValue === 'Saved lists') {
        var savedListName = block.getFieldValue('fieldSavedListsDropdown');
        var quotedListName = generator.quote_(savedListName);
        code = 'self.update_field_list_from_file(' + quotedListName + ')\n';
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
        generator.INDENT + 'self.change_sample(self.app_data.sample_list.index(sample_id), save_analysis= False)\n' +
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

    const plot_type = generator.quote_('field map');
    
    // Insert sub-block statements
    let subBlocksCode = generator.statementToCode(block, 'styling') || ''

    // remove *all* leading spaces:
    subBlocksCode = subBlocksCode.replace(/^ +/gm, '');

    let code = subBlocksCode + '\n';
    const block_id = generator.quote_(block.id);
    code += `self.block_id = ${block_id}\n`;
    // update self.style.style_dict with `style_dict`
    code += 
    `self.plot_style.plot_type =${plot_type}\n` +
    `self.app_data.c_field =${field}\n` +
    `self.app_data.c_field_type =${field_type}\n`;
    // generator.INDENT +`self.update_axis_limits(style_dict, ${field})\n`;
    code += 'self.plot_style.set_style_attributes(self.data[self.app_data.sample_id], self.app_data)\n';
    // 5) Plot
    code += `self.canvas, self.plot_info, _ = plot_map_mpl(parent =self, data = self.data[self.app_data.sample_id], app_data =self.app_data,plot_style =self.plot_style, field_type = ${field_type},field = ${field}, add_histogram=False)\n`;
    code += `self.add_plotwidget_to_plot_viewer(self.plot_info)\n`
    const showMap = block.getFieldValue('SHOW_MAP') === 'TRUE';
    if (showMap) {
    code += `self.show()\n`;
    }
    return code;
};

pythonGenerator.forBlock['plot_correlation'] = function(block, generator) {
    // Retrieve the stored field from the block
    const r_2 = generator.quote_(block.getFieldValue('rSquared'));
    const plot_type = generator.quote_('field map');
    const corr_method = generator.quote_(block.getFieldValue('method'));
    let code = '';
    const block_id = generator.quote_(block.id);
    code += `self.block_id = ${block_id}\n`;
    // Insert sub-block statements
    let subBlocksCode = generator.statementToCode(block, 'exportTable') || ''

    // remove *all* leading spaces:
    if (subBlocksCode !== '' && subBlocksCode !== null){
        subBlocksCode = subBlocksCode.replace(/^ +/gm, '');

        code += subBlocksCode + '\n';
    }
    
    // 5) Plot
    code +=`self.plot_style.plot_type =${plot_type}\n` ;
    code +=`self.app_data.corr_method =${corr_method}\n`;
    code +=`self.app_data.corr_squared =${r_2}\n`;
    code += 'self.plot_style.set_style_attributes(self.data[self.app_data.sample_id], self.app_data)\n';
    code += `canvas, plot_info = plot_correlation(parent=self, data=self.data[self.app_data.sample_id], app_data=self.app_data, plot_style=self.plot_style)\n`;
    code += `self.add_plotwidget_to_plot_viewer(plot_info)\n`;
    code += `self.show()\n`
    return code;
};

pythonGenerator.forBlock['plot_histogram'] = function(block, generator) {
    // Retrieve block fields
    const hist_type = generator.quote_(block.getFieldValue('histType'));
    const field_type = generator.quote_(block.getFieldValue('fieldType'));
    const field = generator.quote_(block.getFieldValue('field'));
    const plot_type = generator.quote_('histogram');

    let code = '';
    const block_id = generator.quote_(block.id);
    code += `self.block_id = ${block_id}\n`;
    // Insert sub-block statements for styling
    let subBlocksCode = generator.statementToCode(block, 'styling') || '';
    // Remove all leading spaces from each line
    subBlocksCode = subBlocksCode.replace(/^ +/gm, '');
    code += subBlocksCode + '\n';

    // Get nBins from histogramOptions, fallback to 100 if unset/blank/0
    let nBinsVal = '100';
    const histOptionsBlock = block.getInputTargetBlock('histogramOptions');
    if (histOptionsBlock && histOptionsBlock.type === 'histogram_options') {
        const userNBins = histOptionsBlock.getFieldValue('nBins');
        // Accept only positive integers, fallback to 100 otherwise
        nBinsVal = (userNBins && Number(userNBins) > 0) ? userNBins : '100';
    }
    code += 
    `self.plot_style.plot_type =${plot_type}\n` +
    `self.app_data.x_field =${field}\n` +
    `self.app_data.x_field_type =${field_type}\n`+
    `self.app_data.hist_plot_style = ${hist_type}\n` +
    `self.app_data.hist_num_bins=${nBinsVal}\n`;
    // Plot command
    code += 'self.plot_style.set_style_attributes(self.data[self.app_data.sample_id], self.app_data)\n';
    code += `canvas, plot_info = plot_histogram(parent=self, data=self.data[self.app_data.sample_id], app_data=self.app_data, plot_style=self.plot_style)\n`;
    code += `self.add_plotwidget_to_plot_viewer(plot_info)\n`;
    code += `self.show()\n`;

    return code;
};


pythonGenerator.forBlock['export_table'] = function(block, generator) {
  // 1) Gather any statements from sub-blocks attached to FIELDS
  //    For example, a 'select_fields_list' block might generate code like:
  //    "fields_data.append(...)"
  let fieldsCode = generator.statementToCode(block, 'fields') || '';
  if (fieldsCode != '' || fieldsCode != null) {
    // 2) Remove leading spaces (optional, if indentation is unwanted)
    fieldsCode = fieldsCode.replace(/^ +/gm, '');

    // 3) Build final statement code
    let code = `
    fields_data = []
    ${fieldsCode}
    self.export_table(fields_data)
    `.trimStart();
    // Return the statement code
    return code + '\n';
  }
  
  
};

pythonGenerator.forBlock['export_figure'] = function(block, generator) {
    const filetype = block.getFieldValue('FILE_TYPE');
    const filename = block.getFieldValue('FILE_NAME');
    let code = '';
    if (filename === "path/filename"){
        code = `self.canvas.save_plot('figure')\n`;
    }
    else{
        const full_filename = `${filename}.${filetype}`;
        // Assuming `self.figure` or `self.canvas.figure` holds the figure object
        code = `self.canvas.save_plot('figure', '${full_filename}')\n`;
    }
    
    return code;
};

pythonGenerator.forBlock['export_data'] = function(block, generator) {
    const filetype = block.getFieldValue('FILE_TYPE');
    const filename = block.getFieldValue('FILE_NAME');
    let code = '';
    if (filename === "path/filename"){
        code = `self.canvas.save_plot('data')\n`;
    }
    else{
        const full_filename = `${filename}.${filetype}`;
        // Assuming `self.figure` or `self.canvas.figure` holds the figure object
        code = `self.canvas.save_plot('data', '${full_filename}')\n`;
    }
    
    return code;
};



////// Style blocks ////////////
// Assuming you have a pythonGenerator object (like Blockly.Python or similar)
// we define forBlock[...] for each new block type:

/***********************************************
 * X Axis Block (Statement)
 ***********************************************/
pythonGenerator.forBlock['x_axis'] = function(block, generator) {
    const rawXLabel = block.getFieldValue('xLabel');
    const xLabel = rawXLabel ? generator.quote_(rawXLabel) : null;
    const xLimMin = block.getFieldValue('xLimMin') || 'None';
    const xLimMax = block.getFieldValue('xLimMax') || 'None';
    const rawXScale = block.getFieldValue('xScaleDropdown');
    const xScale = rawXScale ? generator.quote_(rawXScale) : null;

    const codeLines = [];
    if (xLabel) codeLines.push(`self.xlabel = ${xLabel}`);
    if (xLimMin !== 'None' || xLimMax !== 'None') codeLines.push(`self.xlim = [${xLimMin}, ${xLimMax}]`);
    if (xScale) codeLines.push(`self.xscale = ${xScale}`);

    if (codeLines.length === 0) return '# x_axis block: no fields set\n';
    return '# x_axis block\n' + codeLines.join('\n') + '\n';
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
    if (yLabel)    codeLines.push(`self.ylabel = ${yLabel}`);
    if (yLimMin !== 'None' || yLimMax !== 'None')
        codeLines.push(`self.ylim = [${yLimMin}, ${yLimMax}]`);
    if (yScale)    codeLines.push(`self.yscale = ${yScale}`);

    if (codeLines.length === 0) {
        return '# y_axis block: no fields set\n';
    }

    let code = '# y_axis block\n';
    code += codeLines.join('\n') + '\n';
    return code;
};

  
  
  /***********************************************
   * Z Axis, C Axis, etc.
   ***********************************************/
  // Repeat the same pattern, each updating `style_dict` if you want them all in "Axes"
  // or separate them if c_axis is conceptually different.
pythonGenerator.forBlock['z_axis'] = function(block, generator) {
    const rawZLabel = block.getFieldValue('zLabel');
    const zLabel = rawZLabel ? generator.quote_(rawZLabel) : null;
    const zLimMin = block.getFieldValue('zLimMin') || 'None';
    const zLimMax = block.getFieldValue('zLimMax') || 'None';
    const rawZScale = block.getFieldValue('zScaleDropdown');
    const zScale = rawZScale ? generator.quote_(rawZScale) : null;

    const codeLines = [];
    if (zLabel) codeLines.push(`self.zlabel = ${zLabel}`);
    if (zLimMin !== 'None' || zLimMax !== 'None') codeLines.push(`self.zlim = [${zLimMin}, ${zLimMax}]`);
    if (zScale) codeLines.push(`self.zscale = ${zScale}`);

    if (codeLines.length === 0) return '# z_axis block: no fields set\n';
    return '# z_axis block\n' + codeLines.join('\n') + '\n';
};

  
pythonGenerator.forBlock['c_axis'] = function(block, generator) {
    const rawCLabel = block.getFieldValue('cLabel');
    const cLabel = rawCLabel ? generator.quote_(rawCLabel) : null;
    const cLimMin = block.getFieldValue('cLimMin') || 'None';
    const cLimMax = block.getFieldValue('cLimMax') || 'None';
    const rawCScale = block.getFieldValue('cScaleDropdown');
    const cScale = rawCScale ? generator.quote_(rawCScale) : null;

    const codeLines = [];
    if (cLabel) codeLines.push(`self.clabel = ${cLabel}`);
    if (cLimMin !== 'None' || cLimMax !== 'None') codeLines.push(`self.clim = [${cLimMin}, ${cLimMax}]`);
    if (cScale) codeLines.push(`self.cscale = ${cScale}`);

    if (codeLines.length === 0) return '# c_axis block: no fields set\n';
    return '# c_axis block\n' + codeLines.join('\n') + '\n';
};

  
  
  /***********************************************
   * Font Block => style_dict
   ***********************************************/
  
pythonGenerator.forBlock['font'] = function(block, generator) {
    const rawFont = block.getFieldValue('font');
    const font = rawFont ? generator.quote_(rawFont) : null;
    const rawFontSize = block.getFieldValue('fontSize');
    const fontSize = rawFontSize ? rawFontSize : 'None';

    const codeLines = [];
    if (font) codeLines.push(`self.font = ${font}`);
    if (fontSize !== 'None') codeLines.push(`self.font_size = ${fontSize}`);

    if (codeLines.length === 0) return '# font block: no fields set\n';
    return '# font block\n' + codeLines.join('\n') + '\n';
};
  
  
  /***********************************************
   * Tick Direction => maybe in Axes
   ***********************************************/
pythonGenerator.forBlock['tick_direction'] = function(block, generator) {
    const rawTickDir = block.getFieldValue('tickDirectionDropdown');
    const tickDir = rawTickDir ? generator.quote_(rawTickDir) : null;

    if (!tickDir) return '# tick_direction block: no fields set\n';
    return '# tick_direction block\nself.tick_dir = ' + tickDir + '\n';
};
  
  
  /***********************************************
   * Aspect Ratio => also Axes
   ***********************************************/
pythonGenerator.forBlock['aspect_ratio'] = function(block, generator) {
    const rawAspect = block.getFieldValue('aspectRatio') || '';
    const aspectRatio = rawAspect ? rawAspect : 'None';

    if ((!rawAspect || rawAspect.trim() === '')) return '# aspect_ratio block: no fields set\n';
    return '# aspect_ratio block\nself.aspect_ratio = ' + aspectRatio + '\n';
};
  
  
  /***********************************************
   * Coloring => style_dict
   ***********************************************/
pythonGenerator.forBlock['colormap'] = function(block, generator) {
    const cm = block.getFieldValue('colormap');
    const rawCM = cm ? generator.quote_(cm) : null;
    const reverse = block.getFieldValue('reverse') === 'TRUE';
    const directionVal = block.getFieldValue('direction');
    const direction = directionVal ? generator.quote_(directionVal) : null;

    const codeLines = [];
    if (rawCM) codeLines.push(`self.cmap = ${rawCM}`);
    if (reverse) codeLines.push('self.cbar_reverse = True');
    if (direction) codeLines.push(`self.cbar_dir = ${direction}`);

    if (codeLines.length === 0) return '# colormap block: no fields set\n';
    return '# colormap block\n' + codeLines.join('\n') + '\n';
};
  
  
  /***********************************************
   * Add Scale => style_dict or maybe Axes? 
   ***********************************************/
pythonGenerator.forBlock['add_scale'] = function(block, generator) {
    const rawScaleColor = block.getFieldValue('scaleColor');
    const scaleColor = rawScaleColor ? generator.quote_(rawScaleColor) : null;
    const rawScaleUnits = block.getFieldValue('scaleUnits');
    const scaleUnits = rawScaleUnits ? generator.quote_(rawScaleUnits) : null;
    const scaleLength = block.getFieldValue('scaleLength') || 'None';
    const rawScaleDir = block.getFieldValue('scaleDirection');
    const scaleDirection = rawScaleDir ? generator.quote_(rawScaleDir) : null;

    const codeLines = [];
    if (scaleColor) codeLines.push(`self.overlay_color = ${scaleColor}`);
    if (scaleUnits) codeLines.push(`self.scale_units = ${scaleUnits}`);
    if (scaleLength !== 'None') codeLines.push(`self.scale_length = ${scaleLength}`);
    if (scaleDirection) codeLines.push(`self.scale_dir = ${scaleDirection}`);

    if (codeLines.length === 0) return '# add_scale block: no fields set\n';
    return '# add_scale block\n' + codeLines.join('\n') + '\n';
};
  
  
  /***********************************************
   * Marker Properties => style_dict
   ***********************************************/
pythonGenerator.forBlock['marker_properties'] = function(block, generator) {
    const rawSymbol = block.getFieldValue('markerSymbol');
    const markerSymbol = rawSymbol ? generator.quote_(rawSymbol) : null;
    const markerSize = block.getFieldValue('markerSize') || 'None';
    const rawColor = block.getFieldValue('markerColor');
    const markerColor = rawColor ? generator.quote_(rawColor) : null;

    const codeLines = [];
    if (markerSymbol) codeLines.push(`self.marker = ${markerSymbol}`);
    if (markerSize !== 'None') codeLines.push(`self.marker_size = ${markerSize}`);
    if (markerColor) codeLines.push(`self.marker_color = ${markerColor}`);

    if (codeLines.length === 0) return '# marker_properties block: no fields set\n';
    return '# marker_properties block\n' + codeLines.join('\n') + '\n';
};
  
  /***********************************************
   * transparency => style_dict
   ***********************************************/
pythonGenerator.forBlock['transparency'] = function(block, generator) {
    const transparency = block.getFieldValue('transparency') || 'None';

    if (!transparency || transparency === 'None') return '# transparency block: no fields set\n';
    return '# transparency block\nself.marker_alpha = ' + transparency + '\n';
};



  /***********************************************
   * Line Properties => style_dict or a separate lines_dict
   ***********************************************/
pythonGenerator.forBlock['line_properties'] = function(block, generator) {
    const lineWidth = block.getFieldValue('lineWidth') || 'None';
    const rawLineColor = block.getFieldValue('lineColor');
    const lineColor = rawLineColor ? generator.quote_(rawLineColor) : null;

    const codeLines = [];
    if (lineWidth !== 'None') codeLines.push(`self.line_width = ${lineWidth}`);
    if (lineColor) codeLines.push(`self.line_color = ${lineColor}`);

    if (codeLines.length === 0) return '# line_properties block: no fields set\n';
    return '# line_properties block\n' + codeLines.join('\n') + '\n';
};
  
  
  /***********************************************
   * Color Field => style_dict
   ***********************************************/
pythonGenerator.forBlock['color_field'] = function(block, generator) {
    const rawFieldType = block.getFieldValue('fieldType');
    const fieldType = rawFieldType ? generator.quote_(rawFieldType) : null;
    const rawField = block.getFieldValue('field');
    const field = rawField ? generator.quote_(rawField) : null;

    const codeLines = [];
    if (fieldType) codeLines.push(`self.app_data.c_field_type = ${fieldType}`); // or self.yfield_type or self.cfield_type as per usage
    if (field) codeLines.push(`self.app_data.c_field = ${field}`);              // see note below

    if (codeLines.length === 0) return '# color_field block: no fields set\n';
    return '# color_field block\n' + codeLines.join('\n') + '\n';
};
// NOTE: You may want to split into xfield/yfield/cfield based on context, as per your attribute design.

  
  
  /***********************************************
   * Colormap => style_dict
   ***********************************************/
pythonGenerator.forBlock['show_mass'] = function(block, generator) {
    const showMass = block.getFieldValue('showMass') === 'TRUE';

    if (!showMass) return '# show_mass block: user disabled\n';
    return '# show_mass block\nself.show_mass = True\n';
};
  
  
  /***********************************************
   * Show Mass => style_dict or style_dict or up to you
   ***********************************************/
pythonGenerator.forBlock['show_mass'] = function(block, generator) {
    const showMass = block.getFieldValue('showMass') === 'TRUE';

    if (!showMass) return '# show_mass block: user disabled\n';
    return '# show_mass block\nself.show_mass = True\n';
};

  
  
  /***********************************************
   * Color By Cluster => style_dict
   ***********************************************/
pythonGenerator.forBlock['color_by_cluster'] = function(block, generator) {
    const rawCluster = block.getFieldValue('clusterType');
    const clusterType = rawCluster ? generator.quote_(rawCluster) : null;

    if (!clusterType) return '# color_by_cluster block: no fields set\n';
    return '# color_by_cluster block\nself.cluster_type = ' + clusterType + '\n';
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

