module.exports = function(grunt) {
  grunt.initConfig({
    cfninit: {
      src: 'cfn/reencrypt_template.cfn.json',
      dest: 'dist/dynamodb_reencrypt.cfn.json'
    }
  });

  //Register task for compiling cfn template
  grunt.registerTask('cfn-include', 'Build cloudformation template using cfn-include', function(){
    var compileTemplate = require('cfn-include');
    var path = require('path');
    var config = grunt.config.get('cfninit');

    var getAbsolutePath = function(filePath){
      if(!path.isAbsolute(filePath))
        filePath = path.join(process.cwd(), filePath);
      return filePath;
    };

    //Build source and destination URLS for cfn templates
    var srcUrl = "file://" + getAbsolutePath(config.src);

    //Compile source template
    var done = this.async();
    compileTemplate({ url: srcUrl }).then(function(template){
      //Write compiled template to dest
      grunt.file.write(getAbsolutePath(config.dest), JSON.stringify(template, null, 2));
      done();
    });
  });

  grunt.registerTask('default', ['cfn-include']);
};
