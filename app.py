# app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
import geopandas as gpd
from libpysal import weights
import esda
import json
import os
import tempfile
from werkzeug.utils import secure_filename
import traceback

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

class SpatialAnalysisAPI:
    def __init__(self):
        self.data = None
        self.w = None
        self.results = {}
    
    def load_data(self, file_path, file_type='excel'):
        """加载数据"""
        try:
            if file_type == 'excel':
                self.data = pd.read_excel(file_path)
            elif file_type == 'csv':
                self.data = pd.read_csv(file_path)
            
            # 创建必要的列
            self.data['id'] = range(1, len(self.data) + 1)
            if 'name' in self.data.columns:
                self.data['city'] = pd.Categorical(self.data['name']).codes
            
            return True, "数据加载成功"
        except Exception as e:
            return False, f"数据加载失败: {str(e)}"
    
    def create_spatial_weights(self, lat_col='lat', lon_col='lon'):
        """创建空间权重矩阵"""
        try:
            if 'geometry' in self.data.columns and hasattr(self.data, 'geometry'):
                coords = np.array([(point.x, point.y) for point in self.data.geometry])
            else:
                coords = list(zip(self.data[lon_col], self.data[lat_col]))
            
            self.w = weights.DistanceBand.from_array(
                np.array(coords),
                threshold=weights.min_threshold_distanceBand(np.array(coords)),
                alpha=-2.0,
                binary=False
            )
            return True, "空间权重矩阵创建成功"
        except Exception as e:
            return False, f"创建空间权重矩阵失败: {str(e)}"
    
    def moran_analysis(self, variable, years=None):
        """莫兰指数分析"""
        try:
            results = {}
            
            if years is None:
                years = self.data['year'].unique() if 'year' in self.data.columns else [None]
            
            for year in years:
                if year is not None:
                    data_subset = self.data[self.data['year'] == year]
                else:
                    data_subset = self.data
                
                y = data_subset[variable].values
                moran = esda.Moran(y, self.w)
                
                results[str(year) if year else 'all'] = {
                    'moran_i': float(moran.I),
                    'p_value': float(moran.p_sim),
                    'z_score': float(moran.z_sim)
                }
            
            return True, results
        except Exception as e:
            return False, f"莫兰分析失败: {str(e)}"
    
    def spatial_regression(self, dependent_var, independent_vars, model_type='sdm'):
        """空间回归分析"""
        try:
            from spreg import ML_Lag, ML_Error
            import statsmodels.api as sm
            
            y = self.data[dependent_var].values
            X = self.data[independent_vars].values
            X = sm.add_constant(X)
            
            if model_type == 'sar':
                model = ML_Lag(y, X, w=self.w)
            elif model_type == 'sem':
                model = ML_Error(y, X, w=self.w)
            elif model_type == 'sdm':
                WX = weights.lag_spatial(self.w, X[:, 1:])  # 排除常数项
                X_sdm = np.hstack([X, WX])
                model = ML_Lag(y, X_sdm, w=self.w)
            else:
                return False, "不支持的模型类型"
            
            # 整理结果
            coefficients = []
            for i, var_name in enumerate(['const'] + independent_vars + 
                                        [f'W_{v}' for v in independent_vars] if model_type == 'sdm' else []):
                if i < len(model.betas):
                    coefficients.append({
                        'variable': var_name,
                        'coefficient': float(model.betas[i][0]),
                        'std_error': float(model.std_err[i]),
                        'p_value': float(model.p_values[i])
                    })
            
            results = {
                'coefficients': coefficients,
                'log_likelihood': float(model.logll),
                'r2': float(model.r2) if hasattr(model, 'r2') else None,
                'model_type': model_type
            }
            
            return True, results
        except Exception as e:
            return False, f"空间回归失败: {str(e)}"

# 初始化分析器
spatial_analyzer = SpatialAnalysisAPI()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传数据文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件上传'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 根据文件扩展名确定类型
        file_type = 'excel' if filename.lower().endswith(('.xlsx', '.xls')) else 'csv'
        
        success, message = spatial_analyzer.load_data(file_path, file_type)
        
        if success:
            # 获取数据基本信息
            data_info = {
                'columns': spatial_analyzer.data.columns.tolist(),
                'shape': spatial_analyzer.data.shape,
                'years': spatial_analyzer.data['year'].unique().tolist() if 'year' in spatial_analyzer.data.columns else []
            }
            
            # 创建空间权重矩阵
            spatial_analyzer.create_spatial_weights()
            
            return jsonify({
                'success': True,
                'message': message,
                'data_info': data_info
            })
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@app.route('/api/moran', methods=['POST'])
def moran_analysis():
    """莫兰指数分析"""
    try:
        data = request.json
        variable = data.get('variable')
        years = data.get('years', None)
        
        success, results = spatial_analyzer.moran_analysis(variable, years)
        
        if success:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            return jsonify({'success': False, 'message': results})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'莫兰分析失败: {str(e)}'})

@app.route('/api/regression', methods=['POST'])
def spatial_regression():
    """空间回归分析"""
    try:
        data = request.json
        dependent_var = data.get('dependent_var')
        independent_vars = data.get('independent_vars')
        model_type = data.get('model_type', 'sdm')
        
        success, results = spatial_analyzer.spatial_regression(
            dependent_var, independent_vars, model_type
        )
        
        if success:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            return jsonify({'success': False, 'message': results})
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'空间回归失败: {str(e)}'})

@app.route('/api/data_info', methods=['GET'])
def get_data_info():
    """获取数据信息"""
    try:
        if spatial_analyzer.data is None:
            return jsonify({'success': False, 'message': '没有加载数据'})
        
        data_info = {
            'columns': spatial_analyzer.data.columns.tolist(),
            'shape': spatial_analyzer.data.shape,
            'years': spatial_analyzer.data['year'].unique().tolist() if 'year' in spatial_analyzer.data.columns else [],
            'sample_data': spatial_analyzer.data.head(10).to_dict('records')
        }
        
        return jsonify({'success': True, 'data_info': data_info})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)